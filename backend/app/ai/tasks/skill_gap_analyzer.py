"""Skill gap derivation from existing job match data."""

from __future__ import annotations

import json
import logging
from typing import Any, Literal
from uuid import UUID

from app.ai.client import AIService
from app.ai.prompts.loader import load_prompt
from app.ai.providers.types import CompletionResult
from app.ai.schemas.skill_gap_output import SkillGapAIOutput
from app.core.database import MongoSession
from app.core.exceptions import AppError
from app.models.analysis import Recommendation
from app.models.enums import AIResultType, AIServiceName, RecommendationSourceType
from app.repositories import (
    AIAnalysisResultRepository,
    JobDescriptionRepository,
    JobMatchRepository,
    RecommendationRepository,
)

logger = logging.getLogger(__name__)

PROMPT_FILE = "skill_gap_v1.yaml"
PROMPT_VERSION = "skill_gap_v1"

REQUIRED_WEIGHT = 1.0
PREFERRED_WEIGHT = 0.5

PriorityLabel = Literal["high", "medium", "low"]
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
PRIORITY_TO_INT = {"high": 1, "medium": 2, "low": 3}


def normalize_skill(value: str) -> str:
    return " ".join(value.lower().strip().split())


def skill_in_list(skill: str, candidates: list[str]) -> bool:
    normalized = normalize_skill(skill)
    for candidate in candidates:
        candidate_norm = normalize_skill(candidate)
        if normalized == candidate_norm or normalized in candidate_norm or candidate_norm in normalized:
            return True
    return False


def compute_skill_coverage(
    *,
    required_skills: list[str],
    preferred_skills: list[str],
    supplemental_skills: list[str],
    matched_skills: list[str],
) -> tuple[float, dict[str, Any]]:
    """Coverage: required=1.0 weight, preferred/supplemental=0.5 weight each."""
    weighted_items: list[tuple[str, float, str]] = []
    seen: set[str] = set()

    for skill in required_skills:
        key = normalize_skill(skill)
        if key not in seen:
            weighted_items.append((skill, REQUIRED_WEIGHT, "required"))
            seen.add(key)

    for skill in preferred_skills + supplemental_skills:
        key = normalize_skill(skill)
        if key not in seen:
            weighted_items.append((skill, PREFERRED_WEIGHT, "preferred"))
            seen.add(key)

    if not weighted_items:
        return 100.0, {
            "required_count": 0,
            "preferred_count": 0,
            "matched_weight": 0.0,
            "total_weight": 0.0,
            "formula": "No JD skills listed — coverage defaults to 100%.",
        }

    matched_weight = 0.0
    total_weight = 0.0
    for skill, weight, _ in weighted_items:
        total_weight += weight
        if skill_in_list(skill, matched_skills):
            matched_weight += weight

    coverage = round((matched_weight / total_weight) * 100, 1) if total_weight else 100.0
    return coverage, {
        "required_count": len(required_skills),
        "preferred_count": len(preferred_skills) + len(supplemental_skills),
        "matched_weight": matched_weight,
        "total_weight": total_weight,
        "formula": "Required skills weight 1.0; preferred/tools/technologies weight 0.5 each.",
    }


def derive_missing_with_priority(
    *,
    job_requirements: dict[str, Any],
    matched_skills: list[str],
    missing_from_match: list[str],
) -> list[dict[str, Any]]:
    required = job_requirements.get("required_skills") or []
    preferred = job_requirements.get("preferred_skills") or []
    tools = job_requirements.get("tools") or []
    technologies = job_requirements.get("technologies") or []
    keywords = job_requirements.get("keywords") or []

    supplemental = [s for s in tools + technologies if not skill_in_list(s, required + preferred)]

    candidates: list[str] = []
    for skill in missing_from_match:
        if not skill_in_list(skill, matched_skills) and not skill_in_list(skill, candidates):
            candidates.append(skill)

    for skill in required + preferred + supplemental:
        if not skill_in_list(skill, matched_skills) and not skill_in_list(skill, candidates):
            candidates.append(skill)

    prioritized: list[dict[str, Any]] = []
    for skill in candidates:
        if skill_in_list(skill, required):
            priority: PriorityLabel = "high"
            source = "required"
        elif skill_in_list(skill, preferred) or skill_in_list(skill, supplemental):
            priority = "medium"
            source = "preferred" if skill_in_list(skill, preferred) else "tool_or_technology"
        elif skill_in_list(skill, keywords):
            priority = "low"
            source = "keyword"
        else:
            priority = "medium"
            source = "match_gap"

        prioritized.append(
            {
                "skill": skill,
                "priority": priority,
                "source": source,
            }
        )

    prioritized.sort(key=lambda item: (PRIORITY_ORDER[item["priority"]], item["skill"].lower()))
    return prioritized


class SkillGapAnalyzer:
    """Derives skill gap analysis from an existing JobMatch record."""

    def __init__(self, ai_service: AIService, session: MongoSession) -> None:
        self.ai_service = ai_service
        self.session = session
        self.match_repo = JobMatchRepository(session)
        self.job_repo = JobDescriptionRepository(session)
        self.recommendation_repo = RecommendationRepository(session)
        self.ai_result_repo = AIAnalysisResultRepository(session)

    async def analyze_for_match(self, job_match_id: UUID) -> dict[str, Any]:
        job_match = await self.match_repo.get_by_id(job_match_id)
        if job_match is None:
            raise AppError("Job match not found.", code="match_not_found", status_code=404)

        job = await self.job_repo.get_by_id(job_match.job_description_id)
        if job is None:
            raise AppError("Job description not found.", code="job_not_found", status_code=404)

        breakdown = job_match.breakdown or {}
        meta = breakdown.get("_meta") or {}
        cached_gap = breakdown.get("_skill_gap")
        if cached_gap and cached_gap.get("match_input_hash") == meta.get("match_input_hash"):
            return self._build_response(job_match, job, cached_gap, cached=True)

        job_requirements = {
            k: v
            for k, v in (job.parsed_requirements or {}).items()
            if k != "_matching_context"
        }

        matched_skills = job_match.matched_skills or []
        missing_from_match = job_match.missing_skills or []

        coverage_pct, coverage_meta = compute_skill_coverage(
            required_skills=job_requirements.get("required_skills") or [],
            preferred_skills=job_requirements.get("preferred_skills") or [],
            supplemental_skills=(job_requirements.get("tools") or [])
            + (job_requirements.get("technologies") or []),
            matched_skills=matched_skills,
        )

        missing_prioritized = derive_missing_with_priority(
            job_requirements=job_requirements,
            matched_skills=matched_skills,
            missing_from_match=missing_from_match,
        )

        ai_output, completion = await self._call_ai(
            job_requirements=job_requirements,
            job_raw_text=job.raw_text,
            matched_skills=matched_skills,
            missing_prioritized=missing_prioritized,
        )

        explanation_map = {
            item.skill: item.why_it_matters for item in ai_output.missing_skill_explanations
        }
        missing_skills_enriched = [
            {
                **item,
                "why_it_matters": explanation_map.get(
                    item["skill"],
                    f"Listed as a {item['source']} gap for this role.",
                ),
            }
            for item in missing_prioritized
        ]

        roadmap = [
            {"skill": step.skill, "rationale": step.rationale}
            for step in ai_output.learning_roadmap
        ]

        gap_payload = {
            "match_input_hash": meta.get("match_input_hash"),
            "target_role": job_requirements.get("job_title") or job.title,
            "company": job.company,
            "skill_coverage_percent": coverage_pct,
            "coverage_meta": coverage_meta,
            "missing_skills": missing_skills_enriched,
            "learning_roadmap": roadmap,
            "matched_skills": matched_skills,
            "prompt_version": PROMPT_VERSION,
        }

        updated_breakdown = dict(breakdown)
        updated_breakdown["_skill_gap"] = gap_payload
        await self.match_repo.update(job_match, breakdown=updated_breakdown)

        await self._persist_recommendations(job_match, missing_skills_enriched, roadmap)

        await self.ai_result_repo.create(
            service_name=AIServiceName.JOB_MATCHER,
            input_hash=f"{meta.get('match_input_hash', '')}:skill_gap",
            result_type=AIResultType.SUGGESTIONS,
            payload=gap_payload,
            model_used=completion.model_used,
            prompt_version=PROMPT_VERSION,
            token_usage=completion.token_usage,
            resume_id=job_match.resume_id,
            resume_version_id=job_match.resume_version_id,
            job_description_id=job_match.job_description_id,
            job_match_id=job_match.id,
        )

        return self._build_response(job_match, job, gap_payload, cached=False)

    async def _call_ai(
        self,
        *,
        job_requirements: dict[str, Any],
        job_raw_text: str,
        matched_skills: list[str],
        missing_prioritized: list[dict[str, Any]],
    ) -> tuple[SkillGapAIOutput, Any]:
        if not missing_prioritized:
            empty = CompletionResult(content="{}", model_used="none", token_usage=None)
            return SkillGapAIOutput(), empty

        prompt_data = load_prompt(PROMPT_FILE)
        user_prompt = prompt_data["user_template"].format(
            job_json=json.dumps(job_requirements, indent=2, default=str),
            job_raw_excerpt=job_raw_text[:4000],
            matched_skills=json.dumps(matched_skills),
            missing_skills_json=json.dumps(missing_prioritized, indent=2),
        )

        return await self.ai_service.complete_structured(
            prompt=user_prompt,
            system_prompt=prompt_data["system"],
            output_schema=SkillGapAIOutput,
            prompt_version=PROMPT_VERSION,
        )

    async def _persist_recommendations(
        self,
        job_match: Any,
        missing_skills: list[dict[str, Any]],
        roadmap: list[dict[str, str]],
    ) -> None:
        await self.recommendation_repo.delete_by_job_match_category(job_match.id, "skill_gap")

        roadmap_index = {step["skill"]: index for index, step in enumerate(roadmap)}
        for item in missing_skills:
            await self.recommendation_repo.create(
                resume_id=job_match.resume_id,
                source_type=RecommendationSourceType.JOB_MATCH,
                job_match_id=job_match.id,
                priority=PRIORITY_TO_INT.get(item["priority"], 2),
                category="skill_gap",
                title=item["skill"],
                explanation=item.get("why_it_matters"),
                impact=item["priority"].upper(),
                suggested_action="Acquire this skill to close the gap for the target role.",
                action_items=[
                    {
                        "roadmap_order": roadmap_index.get(item["skill"], 999),
                        "source": item.get("source"),
                    }
                ],
            )

    def _build_response(
        self,
        job_match: Any,
        job: Any,
        gap_payload: dict[str, Any],
        *,
        cached: bool,
    ) -> dict[str, Any]:
        return {
            "job_match_id": job_match.id,
            "job_description_id": job_match.job_description_id,
            "resume_id": job_match.resume_id,
            "resume_version_id": job_match.resume_version_id,
            "cached": cached,
            "target_role": gap_payload.get("target_role"),
            "company": gap_payload.get("company") or job.company,
            "skill_coverage_percent": gap_payload.get("skill_coverage_percent", 0),
            "coverage_meta": gap_payload.get("coverage_meta", {}),
            "matched_skills": gap_payload.get("matched_skills", job_match.matched_skills or []),
            "missing_skills": gap_payload.get("missing_skills", []),
            "learning_roadmap": gap_payload.get("learning_roadmap", []),
            "match_score": job_match.match_score,
            "analyzed_at": job_match.updated_at,
            "prompt_version": gap_payload.get("prompt_version", PROMPT_VERSION),
        }

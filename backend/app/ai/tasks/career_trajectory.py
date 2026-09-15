"""Evidence-grounded career trajectory analysis with deterministic readiness scoring."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.ai.client import AIService
from app.ai.prompts.loader import load_prompt
from app.ai.schemas.trajectory_output import CareerTrajectoryOutput, TrajectoryRoleOutput
from app.ai.utils import hash_resume_content
from app.core.database import MongoSession
from app.core.exceptions import AppError
from app.models.enums import AIResultType, AIServiceName
from app.repositories import AIAnalysisResultRepository, ResumeRepository, ResumeVersionRepository
from app.utils.version_content import get_version_content, resolve_version

PROMPT_FILE = "career_trajectory_v1.yaml"
PROMPT_VERSION = "career_trajectory_v1"


class CareerTrajectoryAnalyzer:
    def __init__(self, ai_service: AIService, session: MongoSession) -> None:
        self.ai_service = ai_service
        self.session = session
        self.resume_repo = ResumeRepository(session)
        self.version_repo = ResumeVersionRepository(session)
        self.ai_result_repo = AIAnalysisResultRepository(session)

    async def analyze(self, resume_id: UUID, *, resume_version_id: UUID | None = None) -> dict[str, Any]:
        resume = await self.resume_repo.get_by_id(resume_id)
        if resume is None:
            raise AppError("Resume not found.", code="resume_not_found", status_code=404)

        version = await resolve_version(
            self.version_repo, resume_id, version_id=resume_version_id, required=False
        )
        parsed = get_version_content(version) if version else resume.parsed_structure
        raw_text = (version.raw_text if version else resume.raw_text) or ""
        if not parsed:
            raise AppError("Resume has not been parsed yet.", code="resume_not_parsed", status_code=422)

        content_hash = f"{hash_resume_content(parsed)}:{PROMPT_VERSION}"
        cached = await self.ai_result_repo.get_by_input_hash_and_service(
            content_hash, AIServiceName.CAREER_TRAJECTORY
        )
        if cached:
            return self._build_response(cached, resume_id, version.id if version else None, cached=True)

        prompt_data = load_prompt(PROMPT_FILE)
        user_prompt = prompt_data["user_template"].format(
            resume_json=json.dumps(parsed, indent=2, default=str),
            raw_text=raw_text[:8000],
        )
        output, completion = await self.ai_service.complete_structured(
            prompt=user_prompt,
            system_prompt=prompt_data["system"],
            output_schema=CareerTrajectoryOutput,
            prompt_version=PROMPT_VERSION,
        )
        payload = self._score_output(output, parsed)
        result = await self.ai_result_repo.create(
            service_name=AIServiceName.CAREER_TRAJECTORY,
            input_hash=content_hash,
            result_type=AIResultType.CAREER_TRAJECTORY,
            payload=payload,
            model_used=completion.model_used,
            prompt_version=PROMPT_VERSION,
            token_usage=completion.token_usage,
            resume_id=resume_id,
            resume_version_id=version.id if version else None,
        )
        return self._build_response(result, resume_id, version.id if version else None, cached=False)

    def _score_output(self, output: CareerTrajectoryOutput, parsed: dict[str, Any]) -> dict[str, Any]:
        corpus = json.dumps(parsed, default=str).lower()
        skills = self._resume_skills(parsed)
        experience = parsed.get("experience") or []
        projects = parsed.get("projects") or []
        evidence_count = len(experience) + len(projects) + len(parsed.get("achievements") or [])
        paths: list[dict[str, Any]] = []
        for path in output.paths:
            required = self._unique(path.required_skills)
            matched = [skill for skill in required if self._mentioned(skill, skills, corpus)]
            skill_score = self._percent(len(matched), len(required), empty=35)
            experience_score = min(100, 35 + min(45, len(experience) * 20) + (20 if path.experience_signals and experience else 0))
            seniority_score = self._seniority_score(path.seniority_level, experience, corpus)
            evidence_score = min(100, 25 + min(50, evidence_count * 15) + (25 if path.resume_evidence else 0))
            alignment_score = self._alignment_score(path, parsed, corpus)
            factors = [
                {"key": "skills", "label": "Skills", "score": skill_score, "weight": 35, "explanation": f"{len(matched)} of {len(required)} role skills are reflected in the resume."},
                {"key": "experience", "label": "Experience", "score": experience_score, "weight": 25, "explanation": f"The resume contains {len(experience)} experience entr{'y' if len(experience) == 1 else 'ies'} relevant to assessing this move."},
                {"key": "seniority", "label": "Seniority", "score": seniority_score, "weight": 15, "explanation": "Seniority estimate is based on role language, tenure signals, and responsibilities present in the resume."},
                {"key": "evidence", "label": "Evidence", "score": evidence_score, "weight": 15, "explanation": f"Evidence includes {evidence_count} experience, project, or achievement record{'s' if evidence_count != 1 else ''}."},
                {"key": "alignment", "label": "Role alignment", "score": alignment_score, "weight": 10, "explanation": "Alignment compares the target role language with titles, summary, skills, and project text."},
            ]
            readiness = round(sum(item["score"] * item["weight"] for item in factors) / 100)
            paths.append({
                "role": path.role,
                "timeframe": path.timeframe,
                "readiness_score": max(0, min(100, readiness)),
                "summary": path.role_fit_reason,
                "matched_skills": matched,
                "skill_gaps": self._unique(path.likely_skill_gaps),
                "proof_gaps": self._unique(path.likely_proof_gaps),
                "factors": factors,
                "next_steps": self._unique(path.next_steps),
            })
        return {
            "current_profile": output.current_profile,
            "profile_summary": output.profile_summary,
            "paths": paths,
            "limitations": output.limitations,
            "analyzed_at": datetime.now(UTC).isoformat(),
        }

    def _resume_skills(self, parsed: dict[str, Any]) -> list[str]:
        value = parsed.get("skills") or []
        return [str(item) for item in value if str(item).strip()]

    def _mentioned(self, value: str, skills: list[str], corpus: str) -> bool:
        normalized = self._normalize(value)
        return any(normalized == self._normalize(skill) or normalized in self._normalize(skill) or self._normalize(skill) in normalized for skill in skills) or normalized in corpus

    def _alignment_score(self, path: TrajectoryRoleOutput, parsed: dict[str, Any], corpus: str) -> int:
        role_tokens = [token for token in re.findall(r"[a-zA-Z]{3,}", path.role.lower()) if token not in {"and", "the", "for"}]
        title_text = " ".join(str(item.get("title", "")) for item in (parsed.get("experience") or []) if isinstance(item, dict)).lower()
        hits = sum(1 for token in role_tokens if token in corpus or token in title_text)
        return min(100, 35 + hits * 15)

    def _seniority_score(self, level: str, experience: list[Any], corpus: str) -> int:
        level_rank = {"entry": 1, "mid": 2, "senior": 3, "lead": 4}.get(level.lower(), 2)
        leadership = any(word in corpus for word in ("led", "mentored", "managed", "leadership"))
        evidence_rank = min(4, max(1, len(experience) + (1 if leadership else 0)))
        return max(25, min(100, 100 - abs(level_rank - evidence_rank) * 22))

    def _percent(self, numerator: int, denominator: int, *, empty: int) -> int:
        return empty if denominator == 0 else round(numerator / denominator * 100)

    def _unique(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            key = self._normalize(value)
            if key and key not in seen:
                seen.add(key)
                result.append(value.strip())
        return result

    def _normalize(self, value: str) -> str:
        return " ".join(value.lower().strip().split())

    def _build_response(self, result: Any, resume_id: UUID, version_id: UUID | None, *, cached: bool) -> dict[str, Any]:
        return {
            "trajectory_id": result.id,
            "resume_id": resume_id,
            "resume_version_id": version_id,
            "cached": cached,
            **result.payload,
            "prompt_version": result.prompt_version or PROMPT_VERSION,
        }

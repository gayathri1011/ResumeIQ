"""Role-targeted resume optimization."""

from __future__ import annotations

import copy
import json
import logging
from typing import Any
from uuid import UUID

from app.core.database import MongoSession

from app.ai.client import AIService
from app.ai.errors import AIOutputValidationError
from app.ai.prompts.loader import load_prompt
from app.ai.schemas.optimize_output import (
    OptimizationChangeOutput,
    ResumeOptimizationAIOutput,
    _flatten_skills,
    _is_hard_violation,
    reconcile_changes,
    repair_optimized_content,
    section_changed,
    validate_change_explanations,
    validate_no_fabricated_content,
    validate_optimized_schema,
    validate_structural_facts_preserved,
)
from app.ai.utils import hash_job_text, hash_optimization_inputs, hash_resume_content
from app.utils.optimization_apply import attach_change_ids
from app.core.exceptions import AppError
from app.models.enums import AIResultType, AIServiceName
from app.repositories import (
    AIAnalysisResultRepository,
    JobDescriptionRepository,
    JobMatchRepository,
    ResumeRepository,
    ResumeVersionRepository,
)
from app.utils.version_content import get_version_content, resolve_version

logger = logging.getLogger(__name__)

PROMPT_FILE = "resume_optimize_v1.yaml"
PROMPT_VERSION = "resume_optimize_v1"
MAX_ATTEMPTS = 3


class ResumeOptimizer:
    """Optimizes resume content for a target role with change explanations."""

    def __init__(self, ai_service: AIService, session: MongoSession) -> None:
        self.ai_service = ai_service
        self.session = session
        self.resume_repo = ResumeRepository(session)
        self.job_repo = JobDescriptionRepository(session)
        self.match_repo = JobMatchRepository(session)
        self.ai_result_repo = AIAnalysisResultRepository(session)
        self.version_repo = ResumeVersionRepository(session)

    async def optimize(
        self,
        resume_id: UUID,
        *,
        target_role: str,
        job_description_id: UUID | None = None,
        job_description_text: str | None = None,
        target_company: str | None = None,
        experience_level: str | None = None,
        resume_version_id: UUID | None = None,
    ) -> dict[str, Any]:
        resume = await self.resume_repo.get_by_id(resume_id)
        if resume is None:
            raise AppError("Resume not found.", code="resume_not_found", status_code=404)

        version = await resolve_version(
            self.version_repo,
            resume_id,
            version_id=resume_version_id,
            required=False,
        )
        if version:
            original = copy.deepcopy(get_version_content(version))
        elif resume.parsed_structure:
            original = copy.deepcopy(resume.parsed_structure)
        else:
            raise AppError(
                "Resume has not been parsed yet. Upload and parse first.",
                code="resume_not_parsed",
                status_code=422,
            )

        # Normalize pipe/comma-joined skills into individual items before AI rewriting.
        if original.get("skills") is not None:
            original["skills"] = _flatten_skills(original.get("skills"))

        role = target_role.strip()
        if not role:
            raise AppError(
                "Target role is required for optimization.",
                code="target_role_required",
                status_code=422,
            )

        content_hash = hash_resume_content(original)
        inline_context_hash = None
        if job_description_text:
            inline_context_hash = hash_job_text(
                f"{target_company or ''}:{experience_level or ''}:{job_description_text}"
            )
        input_hash = hash_optimization_inputs(
            content_hash,
            role,
            job_description_id,
            inline_context_hash=inline_context_hash,
        )

        job_context = "Not provided"
        skill_gap_context = "Not provided"
        job = None
        job_match = None

        if job_description_text:
            job_context = json.dumps(
                {
                    "target_company": target_company,
                    "experience_level": experience_level,
                    "raw_text_excerpt": job_description_text[:8000],
                },
                indent=2,
                default=str,
            )
        elif job_description_id is not None:
            job = await self.job_repo.get_by_id(job_description_id)
            if job is None:
                raise AppError("Job description not found.", code="job_not_found", status_code=404)

            job_context = json.dumps(
                {
                    "title": job.title,
                    "company": job.company,
                    "parsed_requirements": job.parsed_requirements,
                    "raw_text_excerpt": (job.raw_text or "")[:3000],
                },
                indent=2,
                default=str,
            )

            job_match = await self.match_repo.get_latest_for_pair(resume_id, job_description_id)
            if job_match and job_match.breakdown:
                skill_gap = (job_match.breakdown or {}).get("_skill_gap")
                if skill_gap:
                    skill_gap_context = json.dumps(skill_gap, indent=2, default=str)
                else:
                    skill_gap_context = json.dumps(
                        {
                            "matched_skills": job_match.matched_skills or [],
                            "missing_skills": job_match.missing_skills or [],
                            "match_score": job_match.match_score,
                        },
                        indent=2,
                        default=str,
                    )

        cached_ai = await self.ai_result_repo.get_by_input_hash_and_service(
            input_hash,
            AIServiceName.RESUME_OPTIMIZER,
        )
        # Only reuse cache for the same resume — identical PDF uploads get new
        # resume IDs, and cross-resume cache hits break /optimization/latest.
        if (
            cached_ai
            and cached_ai.payload
            and cached_ai.resume_id is not None
            and cached_ai.resume_id == resume_id
        ):
            payload = cached_ai.payload
            return {
                "optimization_id": cached_ai.id,
                "resume_id": resume_id,
                "target_role": payload.get("target_role", role),
                "job_description_id": job_description_id,
                "job_match_id": payload.get("job_match_id"),
                "optimization_mode": payload.get("optimization_mode", "target_role_only"),
                "original_content": payload.get("original_content", original),
                "optimized_content": payload.get("optimized_content"),
                "changes": payload.get("changes", []),
                "prompt_version": payload.get("prompt_version", PROMPT_VERSION),
                "model_used": cached_ai.model_used,
                "cached": True,
            }

        last_error: Exception | None = None
        for attempt in range(MAX_ATTEMPTS):
            try:
                output, completion = await self._call_ai(
                    original=original,
                    target_role=role,
                    job_context=job_context,
                    skill_gap_context=skill_gap_context,
                )

                optimized = copy.deepcopy(output.optimized_content)
                if original.get("_meta") and "_meta" not in optimized:
                    optimized["_meta"] = copy.deepcopy(original["_meta"])

                optimized = repair_optimized_content(original, optimized)
                optimized = validate_optimized_schema(optimized)

                violations: list[str] = []
                violations.extend(validate_structural_facts_preserved(original, optimized))
                violations.extend(validate_no_fabricated_content(original, optimized))
                if violations:
                    hard_violations = [item for item in violations if _is_hard_violation(item)]
                    if hard_violations or attempt < MAX_ATTEMPTS - 1:
                        raise AIOutputValidationError("; ".join(violations))
                    logger.warning(
                        "Allowing soft optimization violations on final attempt: %s",
                        violations,
                    )

                changes = reconcile_changes(
                    original,
                    optimized,
                    output.changes,
                    target_role=role,
                )
                changes = [
                    change
                    for change in changes
                    if section_changed(original, optimized, change["section"])
                ]
                changes = attach_change_ids(changes)
                if attempt < MAX_ATTEMPTS - 1:
                    explanation_violations = validate_change_explanations(
                        original,
                        optimized,
                        changes,
                    )
                    if explanation_violations:
                        raise AIOutputValidationError("; ".join(explanation_violations))

                payload = {
                    "resume_id": str(resume_id),
                    "resume_version_id": str(version.id) if version else (str(resume_version_id) if resume_version_id else None),
                    "target_role": role,
                    "target_company": target_company,
                    "experience_level": experience_level,
                    "job_description_text": job_description_text,
                    "job_description_id": str(job_description_id) if job_description_id else None,
                    "job_match_id": str(job_match.id) if job_match else None,
                    "original_content": original,
                    "optimized_content": optimized,
                    "changes": changes,
                    "prompt_version": PROMPT_VERSION,
                    "optimization_mode": (
                        "jd_grounded"
                        if job_description_id or job_description_text
                        else "target_role_only"
                    ),
                    "review_status": "pending",
                }

                ai_result = await self.ai_result_repo.create(
                    service_name=AIServiceName.RESUME_OPTIMIZER,
                    input_hash=input_hash,
                    result_type=AIResultType.OPTIMIZATION,
                    payload=payload,
                    model_used=completion.model_used,
                    prompt_version=PROMPT_VERSION,
                    token_usage=completion.token_usage,
                    resume_id=resume_id,
                    resume_version_id=version.id if version else resume_version_id,
                    job_description_id=job_description_id,
                    job_match_id=job_match.id if job_match else None,
                )

                return {
                    "optimization_id": ai_result.id,
                    "resume_id": resume_id,
                    "target_role": role,
                    "target_company": target_company,
                    "experience_level": experience_level,
                    "job_description_text": job_description_text,
                    "job_description_id": job_description_id,
                    "job_match_id": job_match.id if job_match else None,
                    "optimization_mode": payload["optimization_mode"],
                    "original_content": original,
                    "optimized_content": optimized,
                    "changes": changes,
                    "prompt_version": PROMPT_VERSION,
                    "model_used": completion.model_used,
                    "cached": False,
                }
            except AIOutputValidationError as exc:
                last_error = exc
                logger.warning(
                    "Optimization attempt %s failed for resume %s: %s",
                    attempt + 1,
                    resume_id,
                    exc,
                )

        raise AIOutputValidationError(
            "Optimized resume failed factual validation. Please try again."
        ) from last_error

    async def _call_ai(
        self,
        *,
        original: dict[str, Any],
        target_role: str,
        job_context: str,
        skill_gap_context: str,
    ) -> tuple[ResumeOptimizationAIOutput, Any]:
        prompt_data = load_prompt(PROMPT_FILE)
        user_prompt = prompt_data["user_template"].format(
            target_role=target_role,
            job_context=job_context,
            skill_gap_context=skill_gap_context,
            resume_json=json.dumps(original, indent=2, default=str),
        )

        return await self.ai_service.complete_structured(
            prompt=user_prompt,
            system_prompt=prompt_data["system"],
            output_schema=ResumeOptimizationAIOutput,
            prompt_version=PROMPT_VERSION,
        )

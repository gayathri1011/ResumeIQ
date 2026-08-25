"""AI-powered role-specific resume version transformation."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.core.database import MongoSession

from app.ai.client import AIService
from app.ai.errors import AIOutputValidationError, AIProviderError
from app.ai.tasks.resume_optimizer import ResumeOptimizer
from app.core.exceptions import AppError
from app.models.enums import AIResultType, AIServiceName, ExperienceLevel
from app.repositories import AIAnalysisResultRepository
from app.utils.transformation_metadata import (
    build_job_match_details,
    build_transformation_insights,
    estimate_transformation_scores,
)

logger = logging.getLogger(__name__)

PROMPT_VERSION = "role_version_transform_v1"


class RoleVersionTransformer:
    """Transforms a master resume into a role-specific version."""

    def __init__(self, ai_service: AIService, session: MongoSession) -> None:
        self.ai_service = ai_service
        self.session = session
        self.ai_result_repo = AIAnalysisResultRepository(session)

    async def transform(
        self,
        resume_id: UUID,
        *,
        master_version_id: UUID,
        target_role: str,
        target_company: str | None = None,
        job_description_text: str | None = None,
        experience_level: ExperienceLevel | None = None,
    ) -> dict[str, Any]:
        role = target_role.strip()
        if not role:
            raise AppError(
                "Target role is required.",
                code="target_role_required",
                status_code=422,
            )

        optimizer = ResumeOptimizer(self.ai_service, self.session)
        try:
            result = await optimizer.optimize(
                resume_id,
                target_role=role,
                resume_version_id=master_version_id,
                job_description_text=job_description_text,
                target_company=target_company,
                experience_level=experience_level.value if experience_level else None,
            )
        except (AIOutputValidationError, AIProviderError) as exc:
            logger.warning("Role transformation failed for resume %s: %s", resume_id, exc)
            raise AppError(
                "Could not generate a valid role-specific resume. Please try again.",
                code="role_transform_failed",
                status_code=422,
                details=str(exc) if exc.code == "ai_output_invalid" else None,
            ) from exc
        except AppError:
            raise
        except Exception as exc:
            logger.exception("Unexpected role transformation failure for resume %s", resume_id)
            raise AppError(
                "Could not generate a valid role-specific resume. Please try again.",
                code="role_transform_failed",
                status_code=422,
            ) from exc

        original = result["original_content"]
        optimized = result["optimized_content"]
        changes = result["changes"]
        insights = build_transformation_insights(
            changes,
            target_role=role,
            original=original,
        )
        job_match_details = build_job_match_details(
            original,
            job_description_text,
            target_role=role,
        )
        scores = estimate_transformation_scores(changes, job_match_details)

        payload = {
            "resume_id": str(resume_id),
            "master_version_id": str(master_version_id),
            "target_role": role,
            "target_company": target_company,
            "job_description_text": job_description_text,
            "experience_level": experience_level.value if experience_level else None,
            "original_content": original,
            "optimized_content": optimized,
            "changes": changes,
            "insights": insights,
            "role_relevance_score": scores["role_relevance_score"],
            "ats_score": scores["ats_score"],
            "job_match_details": job_match_details,
            "prompt_version": PROMPT_VERSION,
            "validation_passed": True,
            "source_optimization_id": str(result["optimization_id"]),
        }

        ai_result = await self.ai_result_repo.create(
            service_name=AIServiceName.ROLE_VERSION_TRANSFORMER,
            input_hash=f"role_version:{result['optimization_id']}",
            result_type=AIResultType.ROLE_TRANSFORMATION,
            payload=payload,
            model_used=result.get("model_used"),
            prompt_version=PROMPT_VERSION,
            token_usage=None,
            resume_id=resume_id,
            resume_version_id=master_version_id,
        )

        return {
            "transformation_id": ai_result.id,
            "resume_id": str(resume_id),
            "master_version_id": str(master_version_id),
            "target_role": role,
            "target_company": target_company,
            "job_description_text": job_description_text,
            "experience_level": experience_level.value if experience_level else None,
            "original_content": original,
            "optimized_content": optimized,
            "changes": changes,
            "insights": insights,
            "role_relevance_score": scores["role_relevance_score"],
            "ats_score": scores["ats_score"],
            "job_match_score": scores["job_match_score"],
            "job_match_details": job_match_details,
            "prompt_version": PROMPT_VERSION,
            "model_used": result.get("model_used"),
            "cached": result.get("cached", False),
        }

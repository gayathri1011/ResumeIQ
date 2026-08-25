"""Job description extraction via AIService."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.database import MongoSession

from app.ai.client import AIService
from app.ai.prompts.loader import load_prompt
from app.ai.schemas.job_output import JobDescriptionExtractionOutput
from app.ai.utils import hash_job_text, normalize_job_text
from app.core.config import settings
from app.core.exceptions import AppError
from app.models.enums import AIResultType, AIServiceName
from app.repositories import (
    AIAnalysisResultRepository,
    JobDescriptionRepository,
    ResumeRepository,
    ResumeVersionRepository,
)

logger = logging.getLogger(__name__)

PROMPT_FILE = "job_analyze_v1.yaml"
PROMPT_VERSION = "job_analyze_v1"


class JobDescriptionAnalyzer:
    """Extracts structured requirements from raw job description text."""

    def __init__(self, ai_service: AIService, session: MongoSession) -> None:
        self.ai_service = ai_service
        self.session = session
        self.job_repo = JobDescriptionRepository(session)
        self.ai_result_repo = AIAnalysisResultRepository(session)
        self.resume_repo = ResumeRepository(session)
        self.version_repo = ResumeVersionRepository(session)

    async def analyze(
        self,
        raw_text: str,
        *,
        user_id: UUID,
        company: str | None = None,
        resume_id: UUID | None = None,
        resume_version_id: UUID | None = None,
    ) -> dict[str, Any]:
        normalized = normalize_job_text(raw_text)
        content_hash = hash_job_text(normalized)

        await self._validate_resume_context(resume_id, resume_version_id)

        cached_ai = await self.ai_result_repo.get_by_input_hash_and_service(
            content_hash,
            AIServiceName.JOB_ANALYZER,
        )
        if cached_ai and cached_ai.job_description_id:
            job = await self.job_repo.get_by_id(cached_ai.job_description_id)
            if job is not None:
                await self._apply_matching_context(
                    job,
                    resume_id=resume_id,
                    resume_version_id=resume_version_id,
                )
                return self._build_response(job, cached_ai, cached=True)

        return await self._run_fresh_analysis(
            raw_text=raw_text,
            normalized=normalized,
            content_hash=content_hash,
            user_id=user_id,
            company=company,
            resume_id=resume_id,
            resume_version_id=resume_version_id,
        )

    async def _validate_resume_context(
        self,
        resume_id: UUID | None,
        resume_version_id: UUID | None,
    ) -> None:
        if resume_id is None:
            if resume_version_id is not None:
                raise AppError(
                    "resume_version_id requires resume_id.",
                    code="invalid_resume_context",
                    status_code=422,
                )
            return

        resume = await self.resume_repo.get_by_id(resume_id)
        if resume is None:
            raise AppError("Resume not found.", code="resume_not_found", status_code=404)

        if resume_version_id is not None:
            version = await self.version_repo.get_by_id(resume_version_id)
            if version is None or version.resume_id != resume_id:
                raise AppError(
                    "Resume version not found for this resume.",
                    code="resume_version_not_found",
                    status_code=404,
                )

    async def _run_fresh_analysis(
        self,
        *,
        raw_text: str,
        normalized: str,
        content_hash: str,
        user_id: UUID,
        company: str | None,
        resume_id: UUID | None,
        resume_version_id: UUID | None,
    ) -> dict[str, Any]:
        output, completion = await self._call_ai(normalized)
        embedding = await self.ai_service.embed(normalized[:8000])

        if len(embedding) != settings.embedding_dimensions:
            raise AppError(
                "Embedding generation returned an unexpected vector size.",
                code="embedding_invalid",
                status_code=502,
            )

        parsed = output.model_dump()
        parsed["_matching_context"] = self._matching_context_payload(
            resume_id,
            resume_version_id,
        )

        title = (output.job_title or "Untitled Position")[:255]
        job = await self.job_repo.create(
            user_id=user_id,
            title=title,
            company=company,
            raw_text=raw_text,
            parsed_requirements=parsed,
            content_embedding=embedding,
        )

        await self.ai_result_repo.create(
            service_name=AIServiceName.JOB_ANALYZER,
            input_hash=content_hash,
            result_type=AIResultType.JD_EXTRACTION,
            payload=parsed,
            model_used=completion.model_used,
            prompt_version=PROMPT_VERSION,
            token_usage=completion.token_usage,
            job_description_id=job.id,
        )

        ai_result = await self.ai_result_repo.get_by_input_hash_and_service(
            content_hash,
            AIServiceName.JOB_ANALYZER,
        )
        return self._build_response(job, ai_result, cached=False)

    async def _call_ai(self, normalized_text: str) -> tuple[JobDescriptionExtractionOutput, Any]:
        prompt_data = load_prompt(PROMPT_FILE)
        user_prompt = prompt_data["user_template"].format(job_text=normalized_text[:12000])

        return await self.ai_service.complete_structured(
            prompt=user_prompt,
            system_prompt=prompt_data["system"],
            output_schema=JobDescriptionExtractionOutput,
            prompt_version=PROMPT_VERSION,
        )

    async def _apply_matching_context(
        self,
        job: Any,
        *,
        resume_id: UUID | None,
        resume_version_id: UUID | None,
    ) -> None:
        if resume_id is None and resume_version_id is None:
            return

        parsed = dict(job.parsed_requirements or {})
        parsed["_matching_context"] = self._matching_context_payload(
            resume_id,
            resume_version_id,
        )
        await self.job_repo.update(job, parsed_requirements=parsed)

    def _matching_context_payload(
        self,
        resume_id: UUID | None,
        resume_version_id: UUID | None,
    ) -> dict[str, str | None]:
        return {
            "resume_id": str(resume_id) if resume_id else None,
            "resume_version_id": str(resume_version_id) if resume_version_id else None,
        }

    def _build_response(
        self,
        job: Any,
        ai_result: Any | None,
        *,
        cached: bool,
    ) -> dict[str, Any]:
        parsed = job.parsed_requirements or {}
        matching = parsed.get("_matching_context") or {}
        extraction = {
            key: parsed.get(key)
            for key in (
                "job_title",
                "required_skills",
                "preferred_skills",
                "experience_requirements",
                "education_requirements",
                "tools",
                "technologies",
                "responsibilities",
                "keywords",
            )
        }

        return {
            "id": job.id,
            "cached": cached,
            "company": job.company,
            "analyzed_at": job.updated_at,
            "prompt_version": ai_result.prompt_version if ai_result else PROMPT_VERSION,
            "has_embedding": job.content_embedding is not None,
            "target_resume_id": matching.get("resume_id"),
            "target_resume_version_id": matching.get("resume_version_id"),
            **extraction,
        }

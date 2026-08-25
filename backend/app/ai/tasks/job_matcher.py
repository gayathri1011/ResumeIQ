"""Semantic and structured resume–job matching."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.database import MongoSession

from app.ai.client import AIService
from app.ai.prompts.loader import load_prompt
from app.ai.schemas.match_output import JobMatchOutput
from app.ai.utils import hash_job_text, hash_match_inputs, hash_resume_content
from app.core.exceptions import AppError
from app.models.enums import AIResultType, AIServiceName
from app.repositories import (
    AIAnalysisResultRepository,
    JobDescriptionRepository,
    JobMatchRepository,
    ResumeRepository,
    ResumeVersionRepository,
)
from app.services.embedding_service import EmbeddingService, semantic_similarity_score

logger = logging.getLogger(__name__)

PROMPT_FILE = "job_match_v1.yaml"
PROMPT_VERSION = "job_match_v1"

SEMANTIC_WEIGHT = 0.30
BREAKDOWN_WEIGHTS = {
    "skills_match": 0.35,
    "experience_match": 0.25,
    "keyword_match": 0.15,
    "project_relevance": 0.15,
    "education_match": 0.10,
}


class JobMatcher:
    """Matches resumes against job descriptions using embeddings and structured AI analysis."""

    def __init__(self, ai_service: AIService, session: MongoSession) -> None:
        self.ai_service = ai_service
        self.session = session
        self.resume_repo = ResumeRepository(session)
        self.version_repo = ResumeVersionRepository(session)
        self.job_repo = JobDescriptionRepository(session)
        self.match_repo = JobMatchRepository(session)
        self.ai_result_repo = AIAnalysisResultRepository(session)
        self.embedding_service = EmbeddingService(ai_service, session)

    async def match(
        self,
        resume_id: UUID,
        job_description_id: UUID,
        *,
        resume_version_id: UUID | None = None,
    ) -> dict[str, Any]:
        resume = await self.resume_repo.get_by_id(resume_id)
        if resume is None:
            raise AppError("Resume not found.", code="resume_not_found", status_code=404)

        job = await self.job_repo.get_by_id(job_description_id)
        if job is None:
            raise AppError("Job description not found.", code="job_not_found", status_code=404)

        if not job.parsed_requirements:
            raise AppError(
                "Job description has not been analyzed yet.",
                code="job_not_analyzed",
                status_code=422,
            )

        if not resume.parsed_structure:
            raise AppError(
                "Resume has not been parsed yet.",
                code="resume_not_parsed",
                status_code=422,
            )

        version = await self._resolve_version(resume_id, resume_version_id)
        resume_hash = hash_resume_content(
            version.content_snapshot if version else resume.parsed_structure
        )
        job_hash = hash_job_text(job.raw_text)
        match_hash = hash_match_inputs(resume_hash, job_hash, version.id if version else None)

        cached = await self._get_cached_match(
            resume_id=resume_id,
            job_description_id=job_description_id,
            resume_version_id=version.id if version else None,
            match_hash=match_hash,
        )
        if cached:
            return self._build_response(cached, cached=True)

        resume_embedding = await self.embedding_service.ensure_resume_embedding(
            resume,
            resume_version=version,
        )

        if job.content_embedding is None:
            raise AppError(
                "Job description embedding is missing. Re-analyze the job first.",
                code="job_embedding_missing",
                status_code=422,
            )

        semantic_score = semantic_similarity_score(
            resume_embedding,
            list(job.content_embedding),
        )

        output, completion = await self._call_ai(
            resume=resume,
            version=version,
            job=job,
            semantic_score=semantic_score,
        )

        structured_avg = self._weighted_breakdown_average(output.breakdown)
        match_score = round(
            SEMANTIC_WEIGHT * semantic_score + (1 - SEMANTIC_WEIGHT) * structured_avg
        )
        match_score = max(0, min(100, match_score))

        keyword_score = float(output.breakdown.keyword_match)
        breakdown_payload = {
            **output.breakdown.model_dump(),
            "explanations": [e.model_dump() for e in output.explanations],
            "summary": output.summary,
            "semantic_weight": SEMANTIC_WEIGHT,
            "structured_weight": 1 - SEMANTIC_WEIGHT,
            "structured_average": structured_avg,
            "_meta": {
                "resume_content_hash": resume_hash,
                "job_content_hash": job_hash,
                "match_input_hash": match_hash,
                "prompt_version": PROMPT_VERSION,
            },
        }

        job_match = await self.match_repo.create(
            resume_id=resume_id,
            resume_version_id=version.id if version else None,
            job_description_id=job_description_id,
            match_score=match_score,
            semantic_score=semantic_score,
            keyword_score=keyword_score,
            breakdown=breakdown_payload,
            matched_skills=output.matched_skills,
            missing_skills=output.missing_skills,
            missing_keywords=output.missing_keywords,
        )

        payload = {
            "match_score": match_score,
            "semantic_score": semantic_score,
            "keyword_score": keyword_score,
            "breakdown": breakdown_payload,
            "matched_skills": output.matched_skills,
            "missing_skills": output.missing_skills,
            "missing_keywords": output.missing_keywords,
            "summary": output.summary,
        }

        await self.ai_result_repo.create(
            service_name=AIServiceName.JOB_MATCHER,
            input_hash=match_hash,
            result_type=AIResultType.MATCH_DETAILS,
            payload=payload,
            model_used=completion.model_used,
            prompt_version=PROMPT_VERSION,
            token_usage=completion.token_usage,
            resume_id=resume_id,
            resume_version_id=version.id if version else None,
            job_description_id=job_description_id,
            job_match_id=job_match.id,
        )

        return self._build_response(job_match, cached=False)

    async def _resolve_version(
        self,
        resume_id: UUID,
        resume_version_id: UUID | None,
    ) -> Any | None:
        if resume_version_id is not None:
            version = await self.version_repo.get_by_id(resume_version_id)
            if version is None or version.resume_id != resume_id:
                raise AppError(
                    "Resume version not found for this resume.",
                    code="resume_version_not_found",
                    status_code=404,
                )
            return version

        versions = await self.version_repo.list_by_resume(resume_id, limit=1)
        return versions[0] if versions else None

    async def _get_cached_match(
        self,
        *,
        resume_id: UUID,
        job_description_id: UUID,
        resume_version_id: UUID | None,
        match_hash: str,
    ) -> Any | None:
        cached_ai = await self.ai_result_repo.get_by_input_hash_and_service(
            match_hash,
            AIServiceName.JOB_MATCHER,
        )
        if cached_ai and cached_ai.job_match_id:
            match = await self.match_repo.get_by_id(cached_ai.job_match_id)
            if match is not None:
                return match

        existing = await self.match_repo.get_latest_for_pair(
            resume_id,
            job_description_id,
            resume_version_id=resume_version_id,
        )
        if existing is None:
            return None

        meta = (existing.breakdown or {}).get("_meta", {})
        if meta.get("match_input_hash") == match_hash:
            return existing
        return None

    async def _call_ai(
        self,
        *,
        resume: Any,
        version: Any | None,
        job: Any,
        semantic_score: float,
    ) -> tuple[JobMatchOutput, Any]:
        prompt_data = load_prompt(PROMPT_FILE)
        parsed = version.content_snapshot if version else resume.parsed_structure
        job_requirements = {
            k: v
            for k, v in (job.parsed_requirements or {}).items()
            if k != "_matching_context"
        }

        user_prompt = prompt_data["user_template"].format(
            semantic_score=round(semantic_score, 1),
            resume_json=json.dumps(parsed, indent=2, default=str),
            job_json=json.dumps(job_requirements, indent=2, default=str),
        )

        return await self.ai_service.complete_structured(
            prompt=user_prompt,
            system_prompt=prompt_data["system"],
            output_schema=JobMatchOutput,
            prompt_version=PROMPT_VERSION,
        )

    def _weighted_breakdown_average(self, breakdown: Any) -> float:
        total = 0.0
        for key, weight in BREAKDOWN_WEIGHTS.items():
            total += getattr(breakdown, key) * weight
        return total

    def _build_response(self, job_match: Any, *, cached: bool) -> dict[str, Any]:
        breakdown = job_match.breakdown or {}
        core_breakdown = {
            k: breakdown.get(k)
            for k in (
                "skills_match",
                "experience_match",
                "keyword_match",
                "project_relevance",
                "education_match",
            )
        }
        return {
            "match_id": job_match.id,
            "cached": cached,
            "resume_id": job_match.resume_id,
            "resume_version_id": job_match.resume_version_id,
            "job_description_id": job_match.job_description_id,
            "match_score": job_match.match_score,
            "semantic_score": job_match.semantic_score,
            "keyword_score": job_match.keyword_score,
            "breakdown": core_breakdown,
            "matched_skills": job_match.matched_skills or [],
            "missing_skills": job_match.missing_skills or [],
            "missing_keywords": job_match.missing_keywords or [],
            "explanations": breakdown.get("explanations", []),
            "summary": breakdown.get("summary", ""),
            "matched_at": job_match.created_at,
            "prompt_version": (breakdown.get("_meta") or {}).get(
                "prompt_version",
                PROMPT_VERSION,
            ),
        }

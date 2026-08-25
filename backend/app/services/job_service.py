"""Orchestrates job description analysis workflows."""

from __future__ import annotations

from uuid import UUID

from app.core.database import MongoSession

from app.ai.client import get_ai_service
from app.ai.tasks.job_analyzer import JobDescriptionAnalyzer
from app.core.exceptions import AppError
from app.core.jd_validation import validate_job_description_text
from app.repositories import JobDescriptionRepository, ResumeRepository, UserRepository
from app.utils.ownership import require_owned_job, require_owned_resume


class JobService:
    """Orchestrates job description ingestion and extraction."""

    def __init__(self, session: MongoSession) -> None:
        self.session = session
        self.job_repo = JobDescriptionRepository(session)
        self.user_repo = UserRepository(session)
        self.resume_repo = ResumeRepository(session)

    async def analyze_job_description(
        self,
        raw_text: str,
        *,
        user_id: UUID,
        company: str | None = None,
        resume_id: UUID | None = None,
        resume_version_id: UUID | None = None,
    ) -> dict:
        validated_text = validate_job_description_text(raw_text)

        if resume_id is not None:
            await require_owned_resume(self.resume_repo, resume_id, user_id)

        analyzer = JobDescriptionAnalyzer(get_ai_service(), self.session)
        return await analyzer.analyze(
            validated_text,
            user_id=user_id,
            company=company,
            resume_id=resume_id,
            resume_version_id=resume_version_id,
        )

    async def get_job_description(self, job_id: UUID, *, user_id: UUID) -> dict:
        job = await require_owned_job(self.job_repo, job_id, user_id)

        analyzer = JobDescriptionAnalyzer(get_ai_service(), self.session)
        data = analyzer._build_response(job, ai_result=None, cached=False)
        data["raw_text"] = job.raw_text
        return data

    async def list_job_descriptions(
        self,
        user_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict]:
        jobs = await self.job_repo.list_by_user(user_id, skip=skip, limit=limit)
        items: list[dict] = []
        for job in jobs:
            parsed = job.parsed_requirements or {}
            items.append(
                {
                    "id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "job_title": parsed.get("job_title"),
                    "created_at": job.created_at,
                    "updated_at": job.updated_at,
                    "has_embedding": job.content_embedding is not None,
                    "required_skills_count": len(parsed.get("required_skills") or []),
                }
            )
        return items

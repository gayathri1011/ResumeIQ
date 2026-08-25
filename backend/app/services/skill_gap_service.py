"""Orchestrates skill gap analysis workflows."""

from __future__ import annotations

from uuid import UUID

from app.core.database import MongoSession

from app.ai.client import get_ai_service
from app.ai.tasks.skill_gap_analyzer import SkillGapAnalyzer
from app.core.exceptions import AppError
from app.repositories import JobDescriptionRepository, JobMatchRepository, ResumeRepository
from app.utils.ownership import require_owned_job, require_owned_resume


class SkillGapService:
    """Skill gap analysis built on top of existing JobMatch records."""

    def __init__(self, session: MongoSession) -> None:
        self.session = session
        self.match_repo = JobMatchRepository(session)
        self.job_repo = JobDescriptionRepository(session)
        self.resume_repo = ResumeRepository(session)

    async def get_skill_gap_for_job(
        self,
        job_description_id: UUID,
        *,
        user_id: UUID,
        resume_id: UUID,
        resume_version_id: UUID | None = None,
    ) -> dict:
        await require_owned_job(self.job_repo, job_description_id, user_id)
        await require_owned_resume(self.resume_repo, resume_id, user_id)

        job_match = await self.match_repo.get_latest_for_pair(
            resume_id,
            job_description_id,
            resume_version_id=resume_version_id,
        )
        if job_match is None:
            raise AppError(
                "No job match found for this resume and job. Run job matching first.",
                code="match_not_found",
                status_code=422,
            )

        analyzer = SkillGapAnalyzer(get_ai_service(), self.session)
        return await analyzer.analyze_for_match(job_match.id)

    async def get_skill_gap_for_resume(
        self,
        resume_id: UUID,
        *,
        user_id: UUID,
        job_id: UUID,
        resume_version_id: UUID | None = None,
    ) -> dict:
        return await self.get_skill_gap_for_job(
            job_id,
            user_id=user_id,
            resume_id=resume_id,
            resume_version_id=resume_version_id,
        )

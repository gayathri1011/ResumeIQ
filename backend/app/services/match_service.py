"""Orchestrates job matching workflows."""

from __future__ import annotations

from uuid import UUID

from app.core.database import MongoSession

from app.ai.client import get_ai_service
from app.ai.tasks.job_matcher import JobMatcher
from app.core.exceptions import AppError
from app.repositories import JobDescriptionRepository, JobMatchRepository, ResumeRepository
from app.utils.ownership import require_owned_job, require_owned_resume


class MatchService:
    """Orchestrates resume–job matching."""

    def __init__(self, session: MongoSession) -> None:
        self.session = session
        self.resume_repo = ResumeRepository(session)
        self.job_repo = JobDescriptionRepository(session)
        self.match_repo = JobMatchRepository(session)

    async def match_resume_to_job(
        self,
        job_description_id: UUID,
        *,
        user_id: UUID,
        resume_id: UUID,
        resume_version_id: UUID | None = None,
    ) -> dict:
        await require_owned_job(self.job_repo, job_description_id, user_id)
        await require_owned_resume(self.resume_repo, resume_id, user_id)

        job = await self.job_repo.get_by_id(job_description_id)

        matcher = JobMatcher(get_ai_service(), self.session)
        result = await matcher.match(
            resume_id,
            job_description_id,
            resume_version_id=resume_version_id,
        )

        parsed = job.parsed_requirements or {}
        result["job_title"] = parsed.get("job_title") or job.title
        result["company"] = job.company
        return result

    async def list_matches_for_resume(
        self,
        resume_id: UUID,
        *,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
        resume_version_id: UUID | None = None,
    ) -> list[dict]:
        await require_owned_resume(self.resume_repo, resume_id, user_id)

        matches = await self.match_repo.list_by_resume(
            resume_id,
            skip=skip,
            limit=limit,
            resume_version_id=resume_version_id,
        )
        jobs = await self.job_repo.get_by_ids(
            [match.job_description_id for match in matches if match.job_description_id]
        )
        items: list[dict] = []
        for match in matches:
            job = jobs.get(match.job_description_id)
            parsed = (job.parsed_requirements or {}) if job else {}
            breakdown = match.breakdown or {}
            items.append(
                {
                    "match_id": match.id,
                    "resume_id": match.resume_id,
                    "resume_version_id": match.resume_version_id,
                    "job_description_id": match.job_description_id,
                    "job_title": parsed.get("job_title") or (job.title if job else None),
                    "company": job.company if job else None,
                    "match_score": match.match_score,
                    "semantic_score": match.semantic_score,
                    "keyword_score": match.keyword_score,
                    "breakdown": {
                        k: breakdown.get(k)
                        for k in (
                            "skills_match",
                            "experience_match",
                            "keyword_match",
                            "project_relevance",
                            "education_match",
                        )
                    },
                    "matched_skills": match.matched_skills or [],
                    "missing_skills": match.missing_skills or [],
                    "missing_keywords": match.missing_keywords or [],
                    "summary": breakdown.get("summary", ""),
                    "matched_at": match.created_at,
                }
            )
        return items

    async def get_latest_match_for_resume(
        self,
        resume_id: UUID,
        *,
        resume_version_id: UUID | None = None,
    ) -> dict | None:
        matches = await self.match_repo.list_by_resume(
            resume_id,
            limit=1,
            resume_version_id=resume_version_id,
        )
        if not matches:
            return None

        match = matches[0]
        jobs = await self.job_repo.get_by_ids([match.job_description_id])
        job = jobs.get(match.job_description_id)
        parsed = (job.parsed_requirements or {}) if job else {}
        breakdown = match.breakdown or {}
        return {
            "match_id": match.id,
            "job_description_id": match.job_description_id,
            "job_title": parsed.get("job_title") or (job.title if job else None),
            "company": job.company if job else None,
            "match_score": match.match_score,
            "semantic_score": match.semantic_score,
            "breakdown": {
                k: breakdown.get(k)
                for k in (
                    "skills_match",
                    "experience_match",
                    "keyword_match",
                    "project_relevance",
                    "education_match",
                )
            },
            "summary": breakdown.get("summary", ""),
            "matched_at": match.created_at,
        }

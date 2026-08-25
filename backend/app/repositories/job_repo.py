import uuid

from beanie.operators import In

from app.core.database import MongoSession
from app.models.job import JobDescription, JobMatch
from app.repositories.base import BaseRepository


class JobDescriptionRepository(BaseRepository[JobDescription]):
    def __init__(self, session: MongoSession) -> None:
        super().__init__(session, JobDescription)

    async def get_by_ids(self, job_ids: list[uuid.UUID]) -> dict[uuid.UUID, JobDescription]:
        if not job_ids:
            return {}
        jobs = await JobDescription.find(In(JobDescription.id, job_ids)).to_list()
        return {job.id: job for job in jobs}

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[JobDescription]:
        return (
            await JobDescription.find(JobDescription.user_id == user_id)
            .sort("-created_at")
            .skip(skip)
            .limit(limit)
            .to_list()
        )


class JobMatchRepository(BaseRepository[JobMatch]):
    def __init__(self, session: MongoSession) -> None:
        super().__init__(session, JobMatch)

    async def get_by_ids(self, match_ids: list[uuid.UUID]) -> dict[uuid.UUID, JobMatch]:
        if not match_ids:
            return {}
        matches = await JobMatch.find(In(JobMatch.id, match_ids)).to_list()
        return {match.id: match for match in matches}

    async def list_by_resume(
        self,
        resume_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
        resume_version_id: uuid.UUID | None = None,
    ) -> list[JobMatch]:
        criteria = [JobMatch.resume_id == resume_id]
        if resume_version_id is not None:
            criteria.append(JobMatch.resume_version_id == resume_version_id)
        return (
            await JobMatch.find(*criteria)
            .sort("-created_at")
            .skip(skip)
            .limit(limit)
            .to_list()
        )

    async def delete_by_ids(self, match_ids: list[uuid.UUID]) -> None:
        if not match_ids:
            return
        await JobMatch.find(In(JobMatch.id, match_ids)).delete()

    async def delete_by_resume_version_id(self, version_id: uuid.UUID) -> list[uuid.UUID]:
        matches = await JobMatch.find(JobMatch.resume_version_id == version_id).to_list()
        match_ids = [match.id for match in matches]
        await self.delete_by_ids(match_ids)
        return match_ids

    async def list_by_job_description(
        self,
        job_description_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[JobMatch]:
        return (
            await JobMatch.find(JobMatch.job_description_id == job_description_id)
            .sort("-created_at")
            .skip(skip)
            .limit(limit)
            .to_list()
        )

    async def get_latest_for_pair(
        self,
        resume_id: uuid.UUID,
        job_description_id: uuid.UUID,
        *,
        resume_version_id: uuid.UUID | None = None,
    ) -> JobMatch | None:
        criteria = [
            JobMatch.resume_id == resume_id,
            JobMatch.job_description_id == job_description_id,
        ]
        if resume_version_id is not None:
            criteria.append(JobMatch.resume_version_id == resume_version_id)
        return await JobMatch.find(*criteria).sort("-created_at").first_or_none()

import uuid

from app.core.database import MongoSession
from app.models.resume import Resume, ResumeVersion
from app.repositories.base import BaseRepository


class ResumeRepository(BaseRepository[Resume]):
    def __init__(self, session: MongoSession) -> None:
        super().__init__(session, Resume)

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
        active_only: bool = True,
    ) -> list[Resume]:
        criteria = [Resume.user_id == user_id]
        if active_only:
            criteria.append(Resume.is_active == True)  # noqa: E712
        return (
            await Resume.find(*criteria)
            .sort("-updated_at")
            .skip(skip)
            .limit(limit)
            .to_list()
        )


class ResumeVersionRepository(BaseRepository[ResumeVersion]):
    def __init__(self, session: MongoSession) -> None:
        super().__init__(session, ResumeVersion)

    async def list_by_resume(
        self,
        resume_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ResumeVersion]:
        return (
            await ResumeVersion.find(ResumeVersion.resume_id == resume_id)
            .sort("-version_number")
            .skip(skip)
            .limit(limit)
            .to_list()
        )

    async def get_by_resume_and_id(
        self,
        resume_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> ResumeVersion | None:
        version = await self.get_by_id(version_id)
        if version is None or version.resume_id != resume_id:
            return None
        return version

    async def get_next_version_number(self, resume_id: uuid.UUID) -> int:
        versions = await self.list_by_resume(resume_id, limit=1)
        if not versions:
            return 1
        return versions[0].version_number + 1

    async def count_by_resume(self, resume_id: uuid.UUID) -> int:
        return await ResumeVersion.find(ResumeVersion.resume_id == resume_id).count()

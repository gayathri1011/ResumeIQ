from __future__ import annotations

from uuid import UUID

from app.ai.client import get_ai_service
from app.ai.tasks.career_trajectory import CareerTrajectoryAnalyzer
from app.core.database import MongoSession
from app.repositories import ResumeRepository
from app.utils.ownership import require_owned_resume


class CareerTrajectoryService:
    def __init__(self, session: MongoSession) -> None:
        self.session = session
        self.resume_repo = ResumeRepository(session)

    async def analyze(
        self,
        resume_id: UUID,
        *,
        user_id: UUID,
        resume_version_id: UUID | None = None,
    ) -> dict:
        await require_owned_resume(self.resume_repo, resume_id, user_id)
        return await CareerTrajectoryAnalyzer(get_ai_service(), self.session).analyze(
            resume_id,
            resume_version_id=resume_version_id,
        )

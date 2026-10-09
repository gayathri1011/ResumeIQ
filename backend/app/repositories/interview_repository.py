from __future__ import annotations

import uuid
from typing import Any

from pymongo import DESCENDING

from app.core.database import MongoSession
from app.models.enums import InterviewStatus
from app.models.interview import InterviewSession
from app.repositories.base import BaseRepository


class InterviewSessionRepository(BaseRepository[InterviewSession]):
    def __init__(self, session: MongoSession) -> None:
        super().__init__(session, InterviewSession)

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
        status: InterviewStatus | None = None,
    ) -> list[InterviewSession]:
        await self._ensure_db()
        criteria: list[Any] = [InterviewSession.user_id == user_id]
        if status is not None:
            criteria.append(InterviewSession.status == status)
        return (
            await InterviewSession.find(*criteria)
            .sort([("created_at", DESCENDING)])
            .skip(skip)
            .limit(limit)
            .to_list()
        )

    async def get_by_id_and_user(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> InterviewSession | None:
        await self._ensure_db()
        return await InterviewSession.find_one(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user_id,
        )

    async def get_active_session_for_user(
        self,
        user_id: uuid.UUID,
    ) -> InterviewSession | None:
        await self._ensure_db()
        return await InterviewSession.find_one(
            InterviewSession.user_id == user_id,
            InterviewSession.status == InterviewStatus.IN_PROGRESS,
        )

from __future__ import annotations

import uuid
from typing import Any

from pymongo import DESCENDING

from app.core.database import MongoSession
from app.models.enums import GrowthPlanStatus
from app.models.growth import CareerGrowthPlan
from app.repositories.base import BaseRepository


class CareerGrowthPlanRepository(BaseRepository[CareerGrowthPlan]):
    def __init__(self, session: MongoSession) -> None:
        super().__init__(session, CareerGrowthPlan)

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 20,
        status: GrowthPlanStatus | None = None,
    ) -> list[CareerGrowthPlan]:
        await self._ensure_db()
        criteria: list[Any] = [CareerGrowthPlan.user_id == user_id]
        if status is not None:
            criteria.append(CareerGrowthPlan.status == status)
        return (
            await CareerGrowthPlan.find(*criteria)
            .sort([("created_at", DESCENDING)])
            .skip(skip)
            .limit(limit)
            .to_list()
        )

    async def get_by_id_and_user(
        self,
        plan_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> CareerGrowthPlan | None:
        await self._ensure_db()
        return await CareerGrowthPlan.find_one(
            CareerGrowthPlan.id == plan_id,
            CareerGrowthPlan.user_id == user_id,
        )

    async def get_latest_by_user(
        self,
        user_id: uuid.UUID,
        *,
        target_role: str | None = None,
    ) -> CareerGrowthPlan | None:
        await self._ensure_db()
        criteria: list[Any] = [
            CareerGrowthPlan.user_id == user_id,
            CareerGrowthPlan.status == GrowthPlanStatus.ACTIVE,
        ]
        if target_role:
            criteria.append(CareerGrowthPlan.target_role == target_role)
        return (
            await CareerGrowthPlan.find(*criteria)
            .sort([("created_at", DESCENDING)])
            .first_or_none()
        )

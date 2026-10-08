from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import AsyncSessionDep, CurrentUserDep
from app.core.exceptions import AppError
from app.core.rate_limit import rate_limit_ai
from app.schemas.growth import (
    CareerGrowthPlanResponse,
    CreateGrowthPlanRequest,
    ProjectRecommendationResponse,
    ReadinessOverviewResponse,
    SyncInterviewResultResponse,
    UpdateMilestoneStatusRequest,
)
from app.services.growth_service import CareerGrowthService

router = APIRouter(prefix="/growth", tags=["growth"])


@router.post(
    "/plans",
    response_model=CareerGrowthPlanResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_ai)],
)
async def create_or_get_growth_plan(
    body: CreateGrowthPlanRequest,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> CareerGrowthPlanResponse:
    service = CareerGrowthService(session)
    plan = await service.create_or_get_plan(current_user.id, body)
    return CareerGrowthService.serialize_plan(plan)


@router.get(
    "/plans/latest",
    response_model=CareerGrowthPlanResponse | None,
)
async def get_latest_growth_plan(
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
    target_role: str | None = Query(default=None),
) -> CareerGrowthPlanResponse | None:
    service = CareerGrowthService(session)
    plan = await service.get_latest_plan(current_user.id, target_role=target_role)
    if plan is None:
        return None
    return CareerGrowthService.serialize_plan(plan)


@router.get(
    "/plans/{plan_id}",
    response_model=CareerGrowthPlanResponse,
)
async def get_growth_plan(
    plan_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> CareerGrowthPlanResponse:
    service = CareerGrowthService(session)
    plan = await service.get_plan_by_id(plan_id, current_user.id)
    return CareerGrowthService.serialize_plan(plan)


@router.get(
    "/plans/{plan_id}/readiness",
    response_model=ReadinessOverviewResponse,
)
async def get_growth_plan_readiness(
    plan_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> ReadinessOverviewResponse:
    service = CareerGrowthService(session)
    plan = await service.get_plan_by_id(plan_id, current_user.id)
    return service.get_readiness_overview(plan)


@router.patch(
    "/plans/{plan_id}/roadmap/{item_id}",
    response_model=CareerGrowthPlanResponse,
)
@router.patch(
    "/plans/{plan_id}/milestones/{item_id}",
    response_model=CareerGrowthPlanResponse,
)
async def update_roadmap_milestone_status(
    plan_id: UUID,
    item_id: str,
    body: UpdateMilestoneStatusRequest,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> CareerGrowthPlanResponse:
    service = CareerGrowthService(session)
    plan = await service.update_milestone_status(plan_id, item_id, current_user.id, body)
    return CareerGrowthService.serialize_plan(plan)


@router.get(
    "/plans/{plan_id}/projects",
    response_model=list[ProjectRecommendationResponse],
)
async def get_growth_plan_projects(
    plan_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> list[ProjectRecommendationResponse]:
    service = CareerGrowthService(session)
    plan = await service.get_plan_by_id(plan_id, current_user.id)
    serialized = CareerGrowthService.serialize_plan(plan)
    return serialized.project_recommendations


@router.post(
    "/plans/{plan_id}/refresh",
    response_model=CareerGrowthPlanResponse,
    dependencies=[Depends(rate_limit_ai)],
)
async def refresh_growth_plan(
    plan_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> CareerGrowthPlanResponse:
    service = CareerGrowthService(session)
    plan = await service.refresh_plan(plan_id, current_user.id)
    return CareerGrowthService.serialize_plan(plan)


@router.post(
    "/plans/{plan_id}/sync-interview/{session_id}",
    response_model=SyncInterviewResultResponse,
)
async def sync_interview_session_to_growth_plan(
    plan_id: UUID,
    session_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> SyncInterviewResultResponse:
    service = CareerGrowthService(session)
    return await service.sync_interview_session(plan_id, session_id, current_user.id)

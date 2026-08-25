from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import AsyncSessionDep, CurrentUserDep
from app.core.rate_limit import rate_limit_ai
from app.schemas.pagination import pagination_params
from app.schemas.job import (
    AnalyzeJobRequest,
    AnalyzeJobResponse,
    JobDescriptionDetailResponse,
    JobDescriptionListItem,
    MatchJobRequest,
    MatchJobResponse,
)
from app.schemas.skill_gap import SkillGapResponse
from app.services.job_service import JobService
from app.services.match_service import MatchService
from app.services.skill_gap_service import SkillGapService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobDescriptionListItem])
async def list_jobs(
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
    pagination: tuple[int, int] = Depends(pagination_params),
) -> list[JobDescriptionListItem]:
    limit, offset = pagination
    service = JobService(session)
    items = await service.list_job_descriptions(current_user.id, skip=offset, limit=limit)
    return [JobDescriptionListItem.model_validate(item) for item in items]


@router.post(
    "/analyze",
    response_model=AnalyzeJobResponse,
    dependencies=[Depends(rate_limit_ai)],
)
async def analyze_job(
    body: AnalyzeJobRequest,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> AnalyzeJobResponse:
    service = JobService(session)
    result = await service.analyze_job_description(
        body.raw_text,
        user_id=current_user.id,
        company=body.company,
        resume_id=body.resume_id,
        resume_version_id=body.resume_version_id,
    )
    return AnalyzeJobResponse.model_validate(result)


@router.get("/{job_id}", response_model=JobDescriptionDetailResponse)
async def get_job(
    job_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> JobDescriptionDetailResponse:
    service = JobService(session)
    data = await service.get_job_description(job_id, user_id=current_user.id)
    return JobDescriptionDetailResponse.model_validate(data)


@router.post(
    "/{job_id}/match",
    response_model=MatchJobResponse,
    dependencies=[Depends(rate_limit_ai)],
)
async def match_job(
    job_id: UUID,
    body: MatchJobRequest,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> MatchJobResponse:
    service = MatchService(session)
    result = await service.match_resume_to_job(
        job_id,
        user_id=current_user.id,
        resume_id=body.resume_id,
        resume_version_id=body.resume_version_id,
    )
    return MatchJobResponse.model_validate(result)


@router.get("/{job_id}/skill-gap", response_model=SkillGapResponse)
async def get_job_skill_gap(
    job_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
    resume_id: UUID = Query(..., description="Resume to analyze gaps for"),
    resume_version_id: UUID | None = Query(default=None),
) -> SkillGapResponse:
    service = SkillGapService(session)
    result = await service.get_skill_gap_for_job(
        job_id,
        user_id=current_user.id,
        resume_id=resume_id,
        resume_version_id=resume_version_id,
    )
    return SkillGapResponse.model_validate(result)

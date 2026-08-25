from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import AsyncSessionDep, CurrentUserDep
from app.core.rate_limit import rate_limit_ai
from app.schemas.bullet import (
    ImproveBulletRequest,
    ImproveBulletResponse,
    ReplaceBulletRequest,
    ReplaceBulletResponse,
    ResumeBulletItem,
)
from app.services.bullet_service import BulletService

router = APIRouter(prefix="/bullets", tags=["bullets"])


@router.post(
    "/improve",
    response_model=ImproveBulletResponse,
    dependencies=[Depends(rate_limit_ai)],
)
async def improve_bullet(
    body: ImproveBulletRequest,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> ImproveBulletResponse:
    service = BulletService(session)
    result = await service.improve_bullet(
        body.bullet_text,
        resume_id=body.resume_id,
        user_id=current_user.id,
        resume_version_id=body.resume_version_id,
        target_role=body.target_role,
        regenerate=body.regenerate,
        previous_improved_text=body.previous_improved_text,
    )
    return ImproveBulletResponse.model_validate(result)


@router.post("/replace", response_model=ReplaceBulletResponse)
async def replace_bullet(
    body: ReplaceBulletRequest,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> ReplaceBulletResponse:
    service = BulletService(session)
    result = await service.replace_bullet(
        resume_id=body.resume_id,
        section=body.section,
        entry_index=body.entry_index,
        bullet_index=body.bullet_index,
        improved_text=body.improved_text,
        user_id=current_user.id,
        resume_version_id=body.resume_version_id,
    )
    return ReplaceBulletResponse.model_validate(result)


@router.get("/resume/{resume_id}", response_model=list[ResumeBulletItem])
async def list_resume_bullets(
    resume_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
    version_id: UUID | None = Query(default=None, alias="versionId"),
) -> list[ResumeBulletItem]:
    service = BulletService(session)
    items = await service.list_bullets(
        resume_id,
        user_id=current_user.id,
        resume_version_id=version_id,
    )
    return [ResumeBulletItem.model_validate(item) for item in items]

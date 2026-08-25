import io
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.api.deps import AsyncSessionDep, CurrentUserDep
from app.core.rate_limit import rate_limit_ai
from app.schemas.pagination import pagination_params
from app.schemas.analysis import AnalyzeResumeResponse, ResumeDetailResponse
from app.schemas.job import MatchJobResponse, ResumeJobMatchListItem
from app.schemas.optimize import (
    ApplyOptimizationRequest,
    ApplyOptimizationResponse,
    OptimizeResumeRequest,
    OptimizeResumeResponse,
)
from app.schemas.resume import ResumeListItem, ResumeUploadResponse
from app.schemas.skill_gap import SkillGapResponse
from app.schemas.version import (
    GenerateRoleVersionRequest,
    GenerateRoleVersionResponse,
    UpdateVersionRequest,
    VersionDetailResponse,
    VersionListItem,
    VersionOptimizeRequest,
    VersionTransformationResponse,
)
from app.services.analysis_service import AnalysisService
from app.services.match_service import MatchService
from app.services.optimizer_service import OptimizerService
from app.services.pdf_service import PdfService
from app.services.resume_service import ResumeService
from app.services.skill_gap_service import SkillGapService
from app.services.version_service import VersionService

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.get("", response_model=list[ResumeListItem])
async def list_resumes(
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
    pagination: tuple[int, int] = Depends(pagination_params),
) -> list[ResumeListItem]:
    limit, offset = pagination
    service = AnalysisService(session)
    items = await service.list_dashboard_resumes(current_user.id, skip=offset, limit=limit)
    return [ResumeListItem.model_validate(item) for item in items]


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
    file: UploadFile = File(...),
) -> ResumeUploadResponse:
    service = ResumeService(session)
    return await service.upload_resume(file, user_id=current_user.id)


@router.get("/{resume_id}", response_model=ResumeDetailResponse)
async def get_resume(
    resume_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
    version_id: UUID | None = Query(default=None, alias="versionId"),
) -> ResumeDetailResponse:
    service = AnalysisService(session)
    data = await service.get_resume_with_analysis(
        resume_id,
        user_id=current_user.id,
        resume_version_id=version_id,
    )
    return ResumeDetailResponse.model_validate(data)


@router.post(
    "/{resume_id}/analyze",
    response_model=AnalyzeResumeResponse,
    dependencies=[Depends(rate_limit_ai)],
)
async def analyze_resume(
    resume_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
    version_id: UUID | None = Query(default=None, alias="versionId"),
) -> AnalyzeResumeResponse:
    service = AnalysisService(session)
    result = await service.analyze_resume(
        resume_id,
        user_id=current_user.id,
        resume_version_id=version_id,
    )
    return AnalyzeResumeResponse.model_validate(result)


@router.get("/{resume_id}/matches", response_model=list[ResumeJobMatchListItem])
async def list_resume_matches(
    resume_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
    version_id: UUID | None = Query(default=None, alias="versionId"),
    pagination: tuple[int, int] = Depends(pagination_params),
) -> list[ResumeJobMatchListItem]:
    limit, offset = pagination
    service = MatchService(session)
    items = await service.list_matches_for_resume(
        resume_id,
        user_id=current_user.id,
        skip=offset,
        limit=limit,
        resume_version_id=version_id,
    )
    return [ResumeJobMatchListItem.model_validate(item) for item in items]


@router.get("/{resume_id}/skill-gap", response_model=SkillGapResponse)
async def get_resume_skill_gap(
    resume_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
    job_id: UUID = Query(..., description="Job description to analyze gaps against"),
    resume_version_id: UUID | None = Query(default=None),
) -> SkillGapResponse:
    service = SkillGapService(session)
    result = await service.get_skill_gap_for_resume(
        resume_id,
        user_id=current_user.id,
        job_id=job_id,
        resume_version_id=resume_version_id,
    )
    return SkillGapResponse.model_validate(result)


@router.post(
    "/{resume_id}/optimize",
    response_model=OptimizeResumeResponse,
    dependencies=[Depends(rate_limit_ai)],
)
async def optimize_resume(
    resume_id: UUID,
    body: OptimizeResumeRequest,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> OptimizeResumeResponse:
    service = OptimizerService(session)
    result = await service.optimize_resume(
        resume_id,
        user_id=current_user.id,
        target_role=body.target_role,
        job_id=body.job_id,
        resume_version_id=body.resume_version_id,
    )
    return OptimizeResumeResponse.model_validate(result)


@router.get("/{resume_id}/optimization/latest", response_model=OptimizeResumeResponse | None)
async def get_latest_optimization(
    resume_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
    version_id: UUID | None = Query(default=None, alias="versionId"),
) -> OptimizeResumeResponse | None:
    service = OptimizerService(session)
    result = await service.get_latest_optimization(
        resume_id,
        user_id=current_user.id,
        resume_version_id=version_id,
    )
    if result is None:
        return None
    return OptimizeResumeResponse.model_validate(result)


@router.post("/{resume_id}/optimization/apply", response_model=ApplyOptimizationResponse)
async def apply_optimization(
    resume_id: UUID,
    body: ApplyOptimizationRequest,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> ApplyOptimizationResponse:
    service = OptimizerService(session)
    result = await service.apply_optimization(
        resume_id,
        body.optimization_id,
        user_id=current_user.id,
        decisions=[item.model_dump() for item in body.decisions] if body.decisions else None,
        bulk_action=body.bulk_action,
        resume_version_id=body.resume_version_id,
    )
    return ApplyOptimizationResponse.model_validate(result)


@router.get("/{resume_id}/versions", response_model=list[VersionListItem])
async def list_versions(
    resume_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
    pagination: tuple[int, int] = Depends(pagination_params),
) -> list[VersionListItem]:
    limit, offset = pagination
    service = VersionService(session)
    items = await service.list_versions(
        resume_id,
        user_id=current_user.id,
        skip=offset,
        limit=limit,
    )
    return [VersionListItem.model_validate(item) for item in items]


@router.post(
    "/{resume_id}/versions/generate",
    response_model=GenerateRoleVersionResponse,
    dependencies=[Depends(rate_limit_ai)],
)
async def generate_role_version(
    resume_id: UUID,
    body: GenerateRoleVersionRequest,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> GenerateRoleVersionResponse:
    service = VersionService(session)
    result = await service.generate_role_version(
        resume_id,
        user_id=current_user.id,
        target_role=body.target_role,
        target_company=body.target_company,
        job_description=body.job_description,
        experience_level=body.experience_level,
        master_version_id=body.master_version_id,
    )
    return GenerateRoleVersionResponse.model_validate(result)


@router.get("/{resume_id}/versions/{version_id}", response_model=VersionDetailResponse)
async def get_version(
    resume_id: UUID,
    version_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> VersionDetailResponse:
    service = VersionService(session)
    result = await service.get_version(resume_id, version_id, user_id=current_user.id)
    return VersionDetailResponse.model_validate(result)


@router.get(
    "/{resume_id}/versions/{version_id}/transformation",
    response_model=VersionTransformationResponse,
)
async def get_version_transformation(
    resume_id: UUID,
    version_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> VersionTransformationResponse:
    service = VersionService(session)
    result = await service.get_version_transformation(
        resume_id,
        version_id,
        user_id=current_user.id,
    )
    return VersionTransformationResponse.model_validate(result)


@router.post("/{resume_id}/versions", response_model=VersionDetailResponse)
async def create_version(
    resume_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
    label: str = Form(...),
    duplicate_from_version_id: UUID | None = Form(default=None),
    file: UploadFile | None = File(default=None),
) -> VersionDetailResponse:
    service = VersionService(session)
    result = await service.create_version(
        resume_id,
        user_id=current_user.id,
        label=label,
        duplicate_from_version_id=duplicate_from_version_id,
        upload=file,
    )
    return VersionDetailResponse.model_validate(result)


@router.patch("/{resume_id}/versions/{version_id}", response_model=VersionDetailResponse)
async def update_version(
    resume_id: UUID,
    version_id: UUID,
    body: UpdateVersionRequest,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> VersionDetailResponse:
    service = VersionService(session)
    result = await service.rename_version(
        resume_id,
        version_id,
        user_id=current_user.id,
        label=body.label,
    )
    return VersionDetailResponse.model_validate(result)


@router.delete("/{resume_id}/versions/{version_id}")
async def delete_version(
    resume_id: UUID,
    version_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> dict:
    service = VersionService(session)
    return await service.delete_version(resume_id, version_id, user_id=current_user.id)


@router.post(
    "/{resume_id}/versions/{version_id}/analyze",
    response_model=AnalyzeResumeResponse,
    dependencies=[Depends(rate_limit_ai)],
)
async def analyze_version(
    resume_id: UUID,
    version_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> AnalyzeResumeResponse:
    service = VersionService(session)
    result = await service.analyze_version(resume_id, version_id, user_id=current_user.id)
    return AnalyzeResumeResponse.model_validate(result)


@router.post(
    "/{resume_id}/versions/{version_id}/optimize",
    response_model=OptimizeResumeResponse,
    dependencies=[Depends(rate_limit_ai)],
)
async def optimize_version(
    resume_id: UUID,
    version_id: UUID,
    body: VersionOptimizeRequest,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> OptimizeResumeResponse:
    service = VersionService(session)
    result = await service.optimize_version(
        resume_id,
        version_id,
        user_id=current_user.id,
        target_role=body.target_role,
        job_id=body.job_id,
    )
    return OptimizeResumeResponse.model_validate(result)


@router.post("/{resume_id}/versions/{version_id}/generate")
async def generate_version_pdf(
    resume_id: UUID,
    version_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> StreamingResponse:
    service = PdfService(session)
    pdf_bytes, filename = await service.generate_version_pdf(
        resume_id,
        version_id,
        user_id=current_user.id,
    )
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )

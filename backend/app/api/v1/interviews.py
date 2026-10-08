from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import AsyncSessionDep, CurrentUserDep
from app.core.rate_limit import rate_limit_ai
from app.models.enums import InterviewStatus
from app.models.interview import InterviewSession
from app.schemas.interview import (
    CreateInterviewSessionRequest,
    InterviewReportResponse,
    InterviewSessionListItem,
    InterviewSessionResponse,
    InterviewTurnResponse,
    SubmitAnswerRequest,
    TurnEvaluationResponse,
)
from app.schemas.pagination import pagination_params
from app.services.interview_service import InterviewService

router = APIRouter(prefix="/interviews", tags=["interviews"])


def _to_session_response(s: InterviewSession) -> InterviewSessionResponse:
    current_q = None
    if s.status != InterviewStatus.COMPLETED and s.current_turn_index < len(s.turns):
        current_q = s.turns[s.current_turn_index].question

    return InterviewSessionResponse(
        id=s.id,
        user_id=s.user_id,
        resume_id=s.resume_id,
        job_description_id=s.job_description_id,
        target_role=s.target_role,
        difficulty=s.difficulty,
        interview_type=s.interview_type,
        status=s.status.value if hasattr(s.status, "value") else str(s.status),
        plan=s.plan,
        current_turn_index=s.current_turn_index,
        turns=[InterviewTurnResponse.model_validate(t.model_dump()) for t in s.turns],
        current_question=current_q,
        overall_score=s.overall_score,
        report=s.report,
        started_at=s.started_at,
        completed_at=s.completed_at,
        created_at=s.created_at,
    )


@router.post(
    "/sessions",
    response_model=InterviewSessionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_ai)],
)
async def create_interview_session(
    body: CreateInterviewSessionRequest,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> InterviewSessionResponse:
    service = InterviewService(session)
    created = await service.create_session(current_user.id, body)
    return _to_session_response(created)


@router.get(
    "/sessions",
    response_model=list[InterviewSessionListItem],
)
async def list_interview_sessions(
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
    pagination: tuple[int, int] = Depends(pagination_params),
) -> list[InterviewSessionListItem]:
    limit, offset = pagination
    service = InterviewService(session)
    return await service.list_sessions(current_user.id, skip=offset, limit=limit)


@router.get(
    "/sessions/{session_id}",
    response_model=InterviewSessionResponse,
)
async def get_interview_session(
    session_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> InterviewSessionResponse:
    service = InterviewService(session)
    interview = await service.get_session(session_id, current_user.id)
    return _to_session_response(interview)


@router.post(
    "/sessions/{session_id}/turns/{turn_index}/answer",
    response_model=TurnEvaluationResponse,
    dependencies=[Depends(rate_limit_ai)],
)
async def submit_turn_answer(
    session_id: UUID,
    turn_index: int,
    body: SubmitAnswerRequest,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> TurnEvaluationResponse:
    service = InterviewService(session)
    return await service.submit_answer(session_id, turn_index, body.answer, current_user.id)


@router.post(
    "/sessions/{session_id}/end",
    response_model=InterviewReportResponse,
)
async def end_interview_session(
    session_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> InterviewReportResponse:
    service = InterviewService(session)
    return await service.end_session(session_id, current_user.id)


@router.post(
    "/sessions/{session_id}/conclude",
    response_model=InterviewReportResponse,
)
async def conclude_interview_session(
    session_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> InterviewReportResponse:
    service = InterviewService(session)
    return await service.end_session(session_id, current_user.id)


@router.get(
    "/sessions/{session_id}/report",
    response_model=InterviewReportResponse,
)
async def get_interview_report(
    session_id: UUID,
    current_user: CurrentUserDep,
    session: AsyncSessionDep,
) -> InterviewReportResponse:
    service = InterviewService(session)
    return await service.get_report(session_id, current_user.id)

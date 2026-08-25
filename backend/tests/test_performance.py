"""Performance-oriented regression tests (query batching, cache reuse)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from types import SimpleNamespace

from app.models.enums import AnalysisStatus
from app.repositories.analysis_repo import ResumeAnalysisRepository
from app.utils.version_status import compute_versions_status_batch


@pytest.mark.asyncio
async def test_get_latest_completed_for_resumes_returns_one_per_resume(monkeypatch):
    session = AsyncMock()
    resume_a = uuid.uuid4()
    resume_b = uuid.uuid4()
    older = SimpleNamespace(
        id=uuid.uuid4(),
        resume_id=resume_a,
        status=AnalysisStatus.COMPLETED,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        overall_score=70,
    )
    newer = SimpleNamespace(
        id=uuid.uuid4(),
        resume_id=resume_a,
        status=AnalysisStatus.COMPLETED,
        created_at=datetime(2026, 2, 1, tzinfo=UTC),
        overall_score=85,
    )
    other = SimpleNamespace(
        id=uuid.uuid4(),
        resume_id=resume_b,
        status=AnalysisStatus.COMPLETED,
        created_at=datetime(2026, 1, 15, tzinfo=UTC),
        overall_score=60,
    )

    repo = ResumeAnalysisRepository(session)
    monkeypatch.setattr(
        "app.repositories.base.ensure_db_initialized",
        AsyncMock(),
    )
    monkeypatch.setattr(
        repo,
        "_list_completed_for_resumes",
        AsyncMock(return_value=[newer, older, other]),
    )
    latest = await repo.get_latest_completed_for_resumes([resume_a, resume_b])

    assert latest[resume_a].overall_score == 85
    assert latest[resume_b].overall_score == 60


@pytest.mark.asyncio
async def test_compute_versions_status_batch_uses_shared_queries(monkeypatch):
    session = AsyncMock()
    resume_id = uuid.uuid4()
    version_one = SimpleNamespace(
        id=uuid.uuid4(),
        resume_id=resume_id,
        version_number=1,
        content_snapshot={"experience": []},
        status=None,
        source=None,
        overall_score=None,
    )
    version_two = SimpleNamespace(
        id=uuid.uuid4(),
        resume_id=resume_id,
        version_number=2,
        content_snapshot={"experience": []},
        status=None,
        source=None,
        overall_score=None,
    )

    analysis_repo = AsyncMock()
    analysis_repo.list_by_resume = AsyncMock(return_value=[])
    match_repo = AsyncMock()
    match_repo.list_by_resume = AsyncMock(return_value=[])
    ai_repo = AsyncMock()
    ai_repo.get_by_resume_analysis_ids = AsyncMock(return_value=[])

    monkeypatch.setattr(
        "app.utils.version_status.ResumeAnalysisRepository",
        lambda _session: analysis_repo,
    )
    monkeypatch.setattr(
        "app.utils.version_status.JobMatchRepository",
        lambda _session: match_repo,
    )
    monkeypatch.setattr(
        "app.utils.version_status.AIAnalysisResultRepository",
        lambda _session: ai_repo,
    )
    statuses = await compute_versions_status_batch(session, [version_one, version_two])

    assert set(statuses.keys()) == {version_one.id, version_two.id}
    analysis_repo.list_by_resume.assert_awaited_once()
    match_repo.list_by_resume.assert_awaited_once()

"""Tests for optimization apply/reject and staleness."""

from __future__ import annotations

import copy
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.client import AIService
from app.ai.providers.mock_provider import MockAIProvider
from app.ai.utils import hash_resume_content
from app.core.database import get_async_session
from app.main import app
from app.models.enums import ResumeVersionSource, ResumeVersionStatus
from app.repositories import ResumeAnalysisRepository, ResumeRepository, ResumeVersionRepository
from app.services.optimizer_service import OptimizerService
from app.utils.optimization_apply import apply_optimization_decisions
from app.utils.resume_staleness import compute_resume_staleness
from tests.test_job_matching import SAMPLE_RESUME_PARSED


def _sample_changes() -> list[dict]:
    return [
        {
            "change_id": "skills",
            "section": "skills",
            "field_path": "skills",
            "before": "Python, SQL, REST APIs",
            "after": "Python, REST APIs, SQL",
            "why": "Reordered skills.",
        },
        {
            "change_id": "experience[0].description",
            "section": "experience",
            "field_path": "experience[0].description",
            "before": "Built backend services with Python and PostgreSQL.",
            "after": "Designed and delivered backend services with Python and PostgreSQL.",
            "why": "Stronger verbs.",
        },
    ]


def test_apply_single_change_updates_only_target_section() -> None:
    original = copy.deepcopy(SAMPLE_RESUME_PARSED)
    optimized = copy.deepcopy(SAMPLE_RESUME_PARSED)
    optimized["skills"] = ["Python", "REST APIs", "SQL"]
    optimized["experience"][0]["description"] = "Designed and delivered backend services."

    updated, accepted = apply_optimization_decisions(
        current_content=original,
        original_content=original,
        optimized_content=optimized,
        changes=_sample_changes(),
        decisions=[{"change_id": "skills", "action": "accept"}],
    )

    assert accepted == ["skills"]
    assert updated["skills"] == ["Python", "REST APIs", "SQL"]
    assert updated["experience"][0]["description"] == original["experience"][0]["description"]


def test_reject_change_keeps_original_content() -> None:
    original = copy.deepcopy(SAMPLE_RESUME_PARSED)
    optimized = copy.deepcopy(SAMPLE_RESUME_PARSED)
    optimized["experience"][0]["description"] = "Designed and delivered backend services."

    updated, accepted = apply_optimization_decisions(
        current_content=original,
        original_content=original,
        optimized_content=optimized,
        changes=_sample_changes(),
        decisions=[{"change_id": "experience[0].description", "action": "reject"}],
    )

    assert accepted == []
    assert updated["experience"][0]["description"] == original["experience"][0]["description"]


@pytest.mark.asyncio
async def test_apply_marks_analysis_and_match_stale(db_session) -> None:
    resume_repo = ResumeRepository(db_session)
    analysis_repo = ResumeAnalysisRepository(db_session)
    version_repo = ResumeVersionRepository(db_session)

    parsed = copy.deepcopy(SAMPLE_RESUME_PARSED)
    resume = await resume_repo.create(
        title="Stale Test",
        parsed_structure=parsed,
        raw_text="resume",
    )
    await version_repo.create(
        resume_id=resume.id,
        version_number=1,
        content_snapshot=parsed,
        raw_text="resume",
        source=ResumeVersionSource.UPLOAD,
        status=ResumeVersionStatus.ACTIVE,
    )
    await analysis_repo.create(
        resume_id=resume.id,
        overall_score=75,
        status="completed",
    )
    await db_session.flush()

    original_hash = hash_resume_content(parsed)
    staleness_before = await compute_resume_staleness(
        db_session,
        resume_id=resume.id,
        parsed_structure=parsed,
    )

    optimized = copy.deepcopy(parsed)
    optimized["skills"] = ["Python", "REST APIs", "SQL"]
    changes = _sample_changes()

    updated, _ = apply_optimization_decisions(
        current_content=parsed,
        original_content=parsed,
        optimized_content=optimized,
        changes=changes,
        decisions=[{"change_id": "skills", "action": "accept"}],
    )
    await resume_repo.update(resume, parsed_structure=updated)
    await db_session.flush()

    staleness_after = await compute_resume_staleness(
        db_session,
        resume_id=resume.id,
        parsed_structure=updated,
    )
    assert hash_resume_content(updated) != original_hash
    assert staleness_after["content_hash"] != original_hash


@pytest.mark.asyncio
async def test_apply_endpoint_accepts_section_change(db_session) -> None:
    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session

    resume_repo = ResumeRepository(db_session)
    version_repo = ResumeVersionRepository(db_session)
    parsed = copy.deepcopy(SAMPLE_RESUME_PARSED)
    resume = await resume_repo.create(
        title="Apply Endpoint",
        parsed_structure=parsed,
        raw_text="resume",
    )
    await version_repo.create(
        resume_id=resume.id,
        version_number=1,
        content_snapshot=parsed,
        raw_text="resume",
        source=ResumeVersionSource.UPLOAD,
        status=ResumeVersionStatus.ACTIVE,
    )
    await db_session.flush()

    with patch("app.services.optimizer_service.get_ai_service") as mock_get:
        mock_get.return_value = AIService(provider=MockAIProvider())
        service = OptimizerService(db_session)
        optimization = await service.optimize_resume(
            resume.id,
            target_role="Backend Engineer",
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/resumes/{resume.id}/optimization/apply",
            json={
                "optimization_id": str(optimization["optimization_id"]),
                "decisions": [
                    {"change_id": "skills", "action": "accept"},
                    {"change_id": "experience[0].description", "action": "reject"},
                ],
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert "skills" in data["accepted_change_ids"]
    assert "experience[0].description" in data["rejected_change_ids"]

    refreshed = await resume_repo.get_by_id(resume.id)
    assert refreshed.parsed_structure["skills"] != parsed["skills"]
    assert (
        refreshed.parsed_structure["experience"][0]["description"]
        == parsed["experience"][0]["description"]
    )


def test_unchanged_section_has_no_change_record() -> None:
    original = copy.deepcopy(SAMPLE_RESUME_PARSED)
    optimized = copy.deepcopy(SAMPLE_RESUME_PARSED)
    changes = _sample_changes()
    education_changes = [change for change in changes if change["section"] == "education"]
    assert education_changes == []

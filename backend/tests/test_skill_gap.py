"""Tests for skill gap analysis."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.providers.mock_provider import _build_valid_skill_gap_output
from app.ai.schemas.skill_gap_output import SkillGapAIOutput
from app.ai.tasks.skill_gap_analyzer import (
    SkillGapAnalyzer,
    compute_skill_coverage,
    derive_missing_with_priority,
)
from app.core.database import get_async_session
from app.main import app
from app.repositories import JobDescriptionRepository, JobMatchRepository, ResumeRepository
from app.ai.client import AIService
from app.ai.providers.mock_provider import MockAIProvider


def test_skill_gap_output_schema_validation() -> None:
    output = SkillGapAIOutput.model_validate(_build_valid_skill_gap_output())
    assert len(output.missing_skill_explanations) >= 1


def test_compute_skill_coverage_weighting() -> None:
    coverage, meta = compute_skill_coverage(
        required_skills=["Python", "AWS"],
        preferred_skills=["Docker"],
        supplemental_skills=["Git"],
        matched_skills=["Python"],
    )
    # required Python (1.0) matched + AWS (1.0) missing + preferred Docker (0.5) + Git (0.5)
    # total weight = 3.0, matched = 1.0 -> 33.3%
    assert coverage == pytest.approx(33.3, rel=0.1)
    assert "Required skills weight 1.0" in meta["formula"]


def test_derive_missing_priority_required_is_high() -> None:
    items = derive_missing_with_priority(
        job_requirements={
            "required_skills": ["Python", "AWS"],
            "preferred_skills": ["Docker"],
            "tools": [],
            "technologies": [],
            "keywords": ["agile"],
        },
        matched_skills=["Python"],
        missing_from_match=["AWS"],
    )
    aws = next(item for item in items if item["skill"] == "AWS")
    assert aws["priority"] == "high"
    docker = next(item for item in items if item["skill"] == "Docker")
    assert docker["priority"] == "medium"


@pytest.mark.asyncio
async def test_skill_gap_cached_on_second_call(db_session) -> None:
    provider = MockAIProvider()
    service = AIService(provider=provider)
    resume_repo = ResumeRepository(db_session)
    job_repo = JobDescriptionRepository(db_session)
    match_repo = JobMatchRepository(db_session)

    resume = await resume_repo.create(
        title="Gap Resume",
        parsed_structure={"skills": ["Python"]},
        raw_text="Python dev",
    )
    job = await job_repo.create(
        title="Engineer",
        raw_text="Need Python and AWS. Preferred Docker.",
        parsed_requirements={
            "job_title": "Engineer",
            "required_skills": ["Python", "AWS"],
            "preferred_skills": ["Docker"],
            "tools": [],
            "technologies": [],
            "keywords": [],
        },
    )
    job_match = await match_repo.create(
        resume_id=resume.id,
        job_description_id=job.id,
        match_score=60,
        matched_skills=["Python"],
        missing_skills=["AWS", "Docker"],
        breakdown={
            "_meta": {"match_input_hash": "abc123"},
            "summary": "partial match",
        },
    )
    await db_session.flush()

    analyzer = SkillGapAnalyzer(service, db_session)
    first = await analyzer.analyze_for_match(job_match.id)
    assert first["cached"] is False
    assert provider.call_count == 1
    assert first["skill_coverage_percent"] < 100

    second = await analyzer.analyze_for_match(job_match.id)
    assert second["cached"] is True
    assert provider.call_count == 1


@pytest.mark.asyncio
async def test_skill_gap_endpoint_requires_match(db_session) -> None:
    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session

    resume_repo = ResumeRepository(db_session)
    job_repo = JobDescriptionRepository(db_session)
    resume = await resume_repo.create(title="R", parsed_structure={"skills": []}, raw_text="x")
    job = await job_repo.create(title="J", raw_text="long enough job description text here")
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/jobs/{job.id}/skill-gap",
            params={"resume_id": str(resume.id)},
        )

    app.dependency_overrides.clear()
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "match_not_found"

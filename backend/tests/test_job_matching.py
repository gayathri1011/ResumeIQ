"""Tests for semantic job matching."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.client import AIService
from app.ai.providers.mock_provider import MockAIProvider, _build_valid_match_output
from app.ai.schemas.match_output import JobMatchOutput
from app.ai.tasks.job_matcher import JobMatcher
from app.core.config import settings
from app.services.embedding_service import cosine_similarity, semantic_similarity_score
from app.core.database import get_async_session
from app.main import app
from app.repositories import JobDescriptionRepository, ResumeRepository
from tests.test_job_analysis import SAMPLE_JD

SAMPLE_RESUME_PARSED = {
    "skills": ["Python", "SQL", "REST APIs"],
    "experience": [
        {
            "title": "Software Engineer",
            "organization": "Tech Co",
            "date_range": "2020 – Present",
            "description": "Built backend services with Python and PostgreSQL.",
        }
    ],
    "education": [
        {
            "title": "B.S. Computer Science",
            "organization": "State University",
            "date_range": "2016 – 2020",
            "description": None,
        }
    ],
    "projects": [
        {
            "title": "API Platform",
            "description": "FastAPI microservices project.",
        }
    ],
    "_meta": {"sections_found": ["skills", "experience", "education", "projects"], "sections_missing": []},
}

UNRELATED_RESUME_PARSED = {
    "skills": [],
    "experience": [{"title": "Retail Associate", "organization": "Store", "description": "Customer service."}],
    "education": [],
    "projects": [],
    "_meta": {"sections_found": ["experience"], "sections_missing": ["skills"]},
}


def test_job_match_output_schema_validation() -> None:
    data = _build_valid_match_output()
    output = JobMatchOutput.model_validate(data)
    assert output.breakdown.skills_match >= 0
    assert isinstance(output.matched_skills, list)


def test_cosine_similarity_identical_vectors() -> None:
    vector = [0.1, 0.2, 0.3]
    score = semantic_similarity_score(vector, vector)
    assert score == 100.0


def test_cosine_similarity_dissimilar_vectors() -> None:
    a = [1.0, 0.0, 0.0]
    b = [0.0, 1.0, 0.0]
    assert cosine_similarity(a, b) == 0.0
    assert semantic_similarity_score(a, b) == 50.0


@pytest.mark.asyncio
async def test_match_dedup_skips_second_ai_call(db_session) -> None:
    provider = MockAIProvider()
    service = AIService(provider=provider)

    resume_repo = ResumeRepository(db_session)
    job_repo = JobDescriptionRepository(db_session)

    resume = await resume_repo.create(
        title="Match Test",
        parsed_structure=SAMPLE_RESUME_PARSED,
        raw_text="Python engineer",
    )
    await db_session.flush()

    job = await job_repo.create(
        title="Senior Software Engineer",
        raw_text=SAMPLE_JD,
        parsed_requirements={
            "job_title": "Senior Software Engineer",
            "required_skills": ["Python", "SQL"],
            "preferred_skills": ["AWS"],
            "technologies": ["FastAPI"],
            "keywords": ["microservices"],
        },
        content_embedding=[0.1] * settings.embedding_dimensions,
    )
    await db_session.flush()

    matcher = JobMatcher(service, db_session)
    first = await matcher.match(resume.id, job.id)
    assert first["cached"] is False
    assert provider.call_count == 1

    second = await matcher.match(resume.id, job.id)
    assert second["cached"] is True
    assert provider.call_count == 1
    assert second["match_id"] == first["match_id"]


@pytest.mark.asyncio
async def test_low_match_for_unrelated_resume(db_session) -> None:
    provider = MockAIProvider()
    service = AIService(provider=provider)
    resume_repo = ResumeRepository(db_session)
    job_repo = JobDescriptionRepository(db_session)

    resume = await resume_repo.create(
        title="Unrelated",
        parsed_structure=UNRELATED_RESUME_PARSED,
        raw_text="unrelated retail",
    )
    await db_session.flush()

    job = await job_repo.create(
        title="Senior Software Engineer",
        raw_text=SAMPLE_JD,
        parsed_requirements={
            "job_title": "Senior Software Engineer",
            "required_skills": ["Python", "SQL", "AWS"],
            "keywords": ["microservices", "CI/CD"],
        },
        content_embedding=[0.9] * settings.embedding_dimensions,
    )
    await db_session.flush()

    matcher = JobMatcher(service, db_session)
    result = await matcher.match(resume.id, job.id)

    assert result["match_score"] < 50
    assert len(result["missing_skills"]) > 0
    assert result["summary"]


@pytest.mark.asyncio
async def test_match_endpoint_with_mock(db_session) -> None:
    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session

    resume_repo = ResumeRepository(db_session)
    job_repo = JobDescriptionRepository(db_session)
    resume = await resume_repo.create(
        title="Endpoint Resume",
        parsed_structure=SAMPLE_RESUME_PARSED,
        raw_text="Python SQL engineer",
        content_embedding=[0.1] * settings.embedding_dimensions,
    )
    job = await job_repo.create(
        title="Engineer",
        raw_text=SAMPLE_JD,
        parsed_requirements={"job_title": "Engineer", "required_skills": ["Python"]},
        content_embedding=[0.1] * settings.embedding_dimensions,
    )
    await db_session.flush()

    with patch("app.services.match_service.get_ai_service") as mock_get:
        mock_get.return_value = AIService(provider=MockAIProvider())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/jobs/{job.id}/match",
                json={"resume_id": str(resume.id)},
            )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["match_score"] is not None
    assert "skills_match" in data["breakdown"]
    assert data["cached"] is False

"""Tests for job description analysis engine."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.client import AIService
from app.ai.providers.mock_provider import MockAIProvider, _build_valid_job_output
from app.ai.schemas.job_output import JobDescriptionExtractionOutput
from app.ai.tasks.job_analyzer import JobDescriptionAnalyzer
from app.ai.utils import hash_job_text
from app.core.config import settings
from app.core.database import get_async_session
from app.core.jd_validation import MIN_JD_WORD_COUNT, validate_job_description_text
from app.main import app
from app.models.enums import AIServiceName
from app.repositories import AIAnalysisResultRepository, JobDescriptionRepository
from app.core.exceptions import AppError
from app.core.security import hash_password


SAMPLE_JD = """
Senior Software Engineer — Backend

We are looking for a Senior Software Engineer to build scalable backend services.

Requirements:
- 5+ years of professional software development experience
- Strong proficiency in Python and SQL
- Experience with REST APIs and PostgreSQL
- Bachelor's degree in Computer Science or equivalent

Preferred:
- AWS and Docker experience
- Familiarity with FastAPI or similar frameworks

Responsibilities:
- Design and implement backend microservices
- Collaborate with product managers and frontend engineers
- Participate in code reviews and mentor junior developers

You will use Git, Jira, and work in an agile CI/CD environment.
""".strip()


def test_job_extraction_output_schema_validation() -> None:
    data = _build_valid_job_output()
    output = JobDescriptionExtractionOutput.model_validate(data)
    assert output.job_title == "Software Engineer"
    assert "Python" in output.required_skills
    assert output.experience_requirements is not None


def test_validate_job_description_rejects_empty() -> None:
    with pytest.raises(AppError) as exc:
        validate_job_description_text("   ")
    assert exc.value.code == "jd_empty"


def test_validate_job_description_rejects_too_short() -> None:
    short = " ".join(["word"] * (MIN_JD_WORD_COUNT - 1))
    with pytest.raises(AppError) as exc:
        validate_job_description_text(short)
    assert exc.value.code == "jd_too_short"


def test_hash_job_text_stable() -> None:
    text = "Senior Engineer\n\nPython and SQL required."
    assert hash_job_text(text) == hash_job_text("  Senior   Engineer\n\nPython and SQL required.  ")


@pytest.mark.asyncio
async def test_ai_service_retry_repair_jd_malformed_then_valid() -> None:
    provider = MockAIProvider(malformed_first=True)
    service = AIService(provider=provider)

    output, result = await service.complete_structured(
        prompt="Extract structured requirements from this job description.",
        system_prompt="job description extraction engine",
        output_schema=JobDescriptionExtractionOutput,
        prompt_version="test",
    )

    assert isinstance(output, JobDescriptionExtractionOutput)
    assert provider.call_count == 2
    assert result.model_used == "mock-model"


@pytest.mark.asyncio
async def test_dedup_skips_second_ai_call(db_session) -> None:
    provider = MockAIProvider()
    service = AIService(provider=provider)
    job_repo = JobDescriptionRepository(db_session)

    from uuid import uuid4

    from app.repositories import UserRepository

    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        email=f"job-cache-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("SecurePass123"),
        full_name="Dev",
    )
    await db_session.flush()

    analyzer = JobDescriptionAnalyzer(service, db_session)
    first = await analyzer.analyze(SAMPLE_JD, user_id=user.id)
    assert first["cached"] is False
    assert provider.call_count == 1

    second = await analyzer.analyze(SAMPLE_JD, user_id=user.id)
    assert second["cached"] is True
    assert provider.call_count == 1
    assert second["id"] == first["id"]

    job = await job_repo.get_by_id(first["id"])
    assert job is not None
    assert job.content_embedding is not None
    assert len(job.content_embedding) == settings.embedding_dimensions


@pytest.mark.asyncio
async def test_embedding_stored_on_fresh_analysis(db_session) -> None:
    provider = MockAIProvider()
    service = AIService(provider=provider)
    job_repo = JobDescriptionRepository(db_session)
    ai_repo = AIAnalysisResultRepository(db_session)

    from uuid import uuid4

    from app.repositories import UserRepository

    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        email=f"job-persist-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("SecurePass123"),
        full_name="Dev",
    )
    await db_session.flush()

    analyzer = JobDescriptionAnalyzer(service, db_session)
    result = await analyzer.analyze(SAMPLE_JD, user_id=user.id, company="Acme Corp")

    job = await job_repo.get_by_id(result["id"])
    assert job is not None
    assert job.content_embedding is not None
    assert len(job.content_embedding) == settings.embedding_dimensions
    assert result["has_embedding"] is True
    assert job.company == "Acme Corp"

    cached = await ai_repo.get_by_input_hash_and_service(
        hash_job_text(SAMPLE_JD),
        AIServiceName.JOB_ANALYZER,
    )
    assert cached is not None
    assert cached.job_description_id == job.id


@pytest.mark.asyncio
async def test_analyze_endpoint_with_mock(db_session) -> None:
    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session

    with patch("app.services.job_service.get_ai_service") as mock_get:
        mock_get.return_value = AIService(provider=MockAIProvider())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/jobs/analyze",
                json={"raw_text": SAMPLE_JD, "company": "Acme"},
            )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["job_title"] is not None
    assert len(data["required_skills"]) > 0
    assert data["cached"] is False
    assert data["has_embedding"] is True


@pytest.mark.asyncio
async def test_analyze_endpoint_rejects_short_jd(db_session) -> None:
    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/jobs/analyze",
            json={"raw_text": "too short"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "jd_too_short"

"""Tests for AI analysis engine."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.client import AIService
from app.ai.providers.mock_provider import MockAIProvider, _build_valid_output
from app.ai.schemas.analysis_output import ResumeAnalysisOutput
from app.ai.tasks.resume_analyzer import ResumeAnalyzer
from app.ai.utils import hash_resume_content
from app.core.database import get_async_session
from app.main import app
from app.models.enums import AIResultType, AIServiceName, AnalysisStatus
from app.repositories import AIAnalysisResultRepository, ResumeAnalysisRepository, ResumeRepository


def test_resume_analysis_output_schema_validation() -> None:
    data = _build_valid_output()
    output = ResumeAnalysisOutput.model_validate(data)
    assert output.overall_score == 68
    assert len(output.dimensions) == 15
    assert "ats" in output.category_scores


@pytest.mark.asyncio
async def test_ai_service_retry_repair_malformed_then_valid() -> None:
    provider = MockAIProvider(malformed_first=True)
    service = AIService(provider=provider)

    output, result = await service.complete_structured(
        prompt="analyze",
        system_prompt="system",
        output_schema=ResumeAnalysisOutput,
        prompt_version="test",
    )

    assert isinstance(output, ResumeAnalysisOutput)
    assert provider.call_count == 2
    assert result.model_used == "mock-model"


@pytest.mark.asyncio
async def test_ai_service_fails_after_exhausted_retries() -> None:
    import json

    from app.ai.errors import AIOutputValidationError

    provider = MockAIProvider()
    service = AIService(provider=provider)

    with patch.object(
        service,
        "_parse_and_validate",
        side_effect=json.JSONDecodeError("bad", "doc", 0),
    ):
        with pytest.raises(AIOutputValidationError):
            await service.complete_structured(
                prompt="analyze",
                system_prompt="system",
                output_schema=ResumeAnalysisOutput,
                prompt_version="test",
            )


@pytest.mark.asyncio
async def test_hash_resume_content_stable() -> None:
    data = {"experience": [{"title": "Engineer"}], "_meta": {"file_size_bytes": 1}}
    h1 = hash_resume_content(data)
    h2 = hash_resume_content({**data, "_meta": {"file_size_bytes": 999}})
    assert h1 == h2


@pytest.mark.asyncio
async def test_dedup_skips_second_ai_call(db_session, sample_pdf) -> None:
    provider = MockAIProvider()
    service = AIService(provider=provider)

    resume_repo = ResumeRepository(db_session)
    analysis_repo = ResumeAnalysisRepository(db_session)
    ai_repo = AIAnalysisResultRepository(db_session)

    from tests.fixtures.resume_factory import SAMPLE_RESUME_TEXT
    from app.parsers.registry import parse_resume_file

    parsed = parse_resume_file(sample_pdf, "sample.pdf", "application/pdf")
    resume = await resume_repo.create(
        title="Test",
        parsed_structure=parsed.structured.to_storage_dict(),
        raw_text=parsed.raw_text,
    )
    await db_session.flush()

    analyzer = ResumeAnalyzer(service, db_session)
    first = await analyzer.analyze(resume.id)
    assert first["cached"] is False
    assert provider.call_count == 1

    second = await analyzer.analyze(resume.id)
    assert second["cached"] is True
    assert provider.call_count == 1

    cached = await ai_repo.get_by_input_hash_and_service(
        hash_resume_content(resume.parsed_structure),
        AIServiceName.RESUME_ANALYZER,
    )
    assert cached is not None


@pytest.mark.asyncio
async def test_missing_certifications_not_fabricated(db_session) -> None:
    provider = MockAIProvider()
    service = AIService(provider=provider)

    parsed_structure = {
        "experience": [{"title": "Engineer"}],
        "skills": ["Python"],
        "_meta": {"sections_found": ["experience", "skills"], "sections_missing": ["certifications"]},
    }

    resume_repo = ResumeRepository(db_session)
    resume = await resume_repo.create(
        title="No Certs",
        parsed_structure=parsed_structure,
        raw_text="Engineer with Python",
    )
    await db_session.flush()

    analyzer = ResumeAnalyzer(service, db_session)
    result = await analyzer.analyze(resume.id)

    cert_dim = next(d for d in result["dimensions"] if d["key"] == "certifications")
    assert "not found" in cert_dim["explanation"].lower() or "missing" in cert_dim["explanation"].lower()
    assert "AWS" not in cert_dim["explanation"]
    assert "Google" not in cert_dim["explanation"]


@pytest.mark.asyncio
async def test_analyze_endpoint_with_mock(db_session, sample_pdf) -> None:
    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session

    from app.parsers.registry import parse_resume_file

    parsed = parse_resume_file(sample_pdf, "sample.pdf", "application/pdf")
    resume_repo = ResumeRepository(db_session)
    resume = await resume_repo.create(
        title="Endpoint Test",
        parsed_structure=parsed.structured.to_storage_dict(),
        raw_text=parsed.raw_text,
    )
    await db_session.flush()

    with patch("app.services.analysis_service.get_ai_service") as mock_get:
        mock_get.return_value = AIService(provider=MockAIProvider())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/api/v1/resumes/{resume.id}/analyze")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["overall_score"] is not None
    assert len(data["dimensions"]) == 15
    assert data["cached"] is False

    await db_session.commit()

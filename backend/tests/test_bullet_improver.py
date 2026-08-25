"""Tests for AI bullet point improvement."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.client import AIService
from app.ai.errors import AIOutputValidationError, AIProviderError
from app.ai.providers.mock_provider import MockAIProvider
from app.ai.providers.types import CompletionResult
from app.ai.schemas.bullet_output import find_fabricated_metrics
from app.ai.tasks.bullet_improver import BulletPointImprover
from app.core.database import get_async_session
from app.main import app
from app.models.enums import ResumeVersionSource, ResumeVersionStatus
from app.repositories import ResumeRepository, ResumeVersionRepository
from app.utils.bullet_utils import list_resume_bullets, replace_resume_bullet


WEAK_BULLET = "Worked on backend stuff and helped the team with APIs"


def test_find_fabricated_metrics_detects_new_numbers() -> None:
    fabricated = find_fabricated_metrics(
        WEAK_BULLET,
        "Improved API performance by 40% through backend optimization.",
    )
    assert "40" in fabricated or "40%" in fabricated


def test_find_fabricated_metrics_allows_placeholders() -> None:
    fabricated = find_fabricated_metrics(
        WEAK_BULLET,
        "Led backend API work [add measurable outcome, e.g. % improvement or team size].",
    )
    assert fabricated == set()


@pytest.mark.asyncio
async def test_improver_does_not_accept_fabricated_metrics() -> None:
    class FabricatingProvider(MockAIProvider):
        async def complete(self, messages, **kwargs):
            return CompletionResult(
                content='{"improved_text": "Boosted throughput by 35%.", "changes_summary": "Added metric.", "metric_placeholder_used": false, "suggested_metric_prompt": null}',
                model_used="fabricate-mock",
                token_usage={"input": 1, "output": 1, "total": 2},
            )

    improver = BulletPointImprover(AIService(provider=FabricatingProvider()))
    with pytest.raises(AIOutputValidationError):
        await improver.improve(WEAK_BULLET)


@pytest.mark.asyncio
async def test_improver_uses_placeholder_for_metricless_bullet() -> None:
    provider = MockAIProvider()
    improver = BulletPointImprover(AIService(provider=provider))
    result = await improver.improve(WEAK_BULLET)

    assert result["metric_placeholder_used"] is True
    assert "[" in result["improved_text"]
    assert "40" not in result["improved_text"]
    assert "35" not in result["improved_text"]


@pytest.mark.asyncio
async def test_regenerate_produces_different_output() -> None:
    provider = MockAIProvider()
    improver = BulletPointImprover(AIService(provider=provider))

    first = await improver.improve(WEAK_BULLET, regenerate=False)
    second = await improver.improve(
        WEAK_BULLET,
        regenerate=True,
        previous_improved_text=first["improved_text"],
    )

    assert first["improved_text"] != second["improved_text"]
    assert second["regenerate"] is True


@pytest.mark.asyncio
async def test_replace_bullet_persists_in_resume(db_session) -> None:
    resume_repo = ResumeRepository(db_session)
    version_repo = ResumeVersionRepository(db_session)

    parsed = {
        "experience": [
            {
                "title": "Engineer",
                "organization": "Acme",
                "date_range": "2020 - Present",
                "description": "Worked on backend stuff\nHelped with APIs",
            }
        ],
        "projects": [],
    }
    resume = await resume_repo.create(
        title="Bullet Test",
        parsed_structure=parsed,
        raw_text="Engineer resume",
    )
    await version_repo.create(
        resume_id=resume.id,
        version_number=1,
        content_snapshot=parsed,
        raw_text="Engineer resume",
        source=ResumeVersionSource.UPLOAD,
        status=ResumeVersionStatus.ACTIVE,
    )
    await db_session.flush()

    updated = replace_resume_bullet(
        parsed,
        section="experience",
        entry_index=0,
        bullet_index=0,
        new_text="Designed and maintained backend APIs with clear ownership.",
    )
    await resume_repo.update(resume, parsed_structure=updated)
    versions = await version_repo.list_by_resume(resume.id, limit=1)
    await version_repo.update(versions[0], content_snapshot=updated)
    await db_session.flush()

    refreshed = await resume_repo.get_by_id(resume.id)
    bullets = list_resume_bullets(refreshed.parsed_structure)
    assert bullets[0]["text"] == "Designed and maintained backend APIs with clear ownership."


@pytest.mark.asyncio
async def test_improve_endpoint_with_mock(db_session) -> None:
    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session

    with patch("app.services.bullet_service.get_ai_service") as mock_get:
        mock_get.return_value = AIService(provider=MockAIProvider())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/bullets/improve",
                json={"bullet_text": WEAK_BULLET},
            )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["original_text"] == WEAK_BULLET
    assert data["improved_text"]
    assert data["changes_summary"]
    assert data["metric_placeholder_used"] is True


@pytest.mark.asyncio
async def test_regenerate_endpoint_distinct_from_improve(db_session) -> None:
    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session

    with patch("app.services.bullet_service.get_ai_service") as mock_get:
        mock_get.return_value = AIService(provider=MockAIProvider())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post(
                "/api/v1/bullets/improve",
                json={"bullet_text": WEAK_BULLET, "regenerate": False},
            )
            second = await client.post(
                "/api/v1/bullets/improve",
                json={
                    "bullet_text": WEAK_BULLET,
                    "regenerate": True,
                    "previous_improved_text": first.json()["improved_text"],
                },
            )

    app.dependency_overrides.clear()

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["improved_text"] != second.json()["improved_text"]
    assert second.json()["regenerate"] is True


@pytest.mark.asyncio
async def test_replace_endpoint_persists(db_session) -> None:
    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session

    resume_repo = ResumeRepository(db_session)
    parsed = {
        "experience": [
            {
                "title": "Engineer",
                "organization": "Acme",
                "date_range": "2020 - Present",
                "description": WEAK_BULLET,
            }
        ],
    }
    resume = await resume_repo.create(
        title="Replace Endpoint",
        parsed_structure=parsed,
        raw_text="text",
    )
    await db_session.flush()

    improved = "Designed and maintained backend APIs with clear ownership."

    with patch("app.services.bullet_service.get_ai_service") as mock_get:
        mock_get.return_value = AIService(provider=MockAIProvider())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/bullets/replace",
                json={
                    "resume_id": str(resume.id),
                    "section": "experience",
                    "entry_index": 0,
                    "bullet_index": 0,
                    "improved_text": improved,
                },
            )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    refreshed = await resume_repo.get_by_id(resume.id)
    bullets = list_resume_bullets(refreshed.parsed_structure)
    assert bullets[0]["text"] == improved


@pytest.mark.asyncio
async def test_improve_endpoint_ai_failure(db_session) -> None:
    class FailingProvider(MockAIProvider):
        async def complete(self, messages, **kwargs):
            raise AIProviderError("AI unavailable for test.")

    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session

    with patch("app.services.bullet_service.get_ai_service") as mock_get:
        mock_get.return_value = AIService(provider=FailingProvider())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/bullets/improve",
                json={"bullet_text": WEAK_BULLET},
            )

    app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "ai_provider_error"

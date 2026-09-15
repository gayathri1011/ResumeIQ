from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.client import AIService
from app.ai.providers.mock_provider import MockAIProvider
from app.ai.tasks.recruiter_lens import RecruiterLensAnalyzer
from app.core.database import get_async_session
from app.core.security import create_access_token, hash_password
from app.main import app
from app.repositories import ResumeRepository, UserRepository
from tests.test_job_matching import SAMPLE_RESUME_PARSED


@pytest.mark.asyncio
async def test_recruiter_lens_scores_are_deterministic_and_cached(db_session) -> None:
    resume = await ResumeRepository(db_session).create(
        title="Recruiter lens test",
        parsed_structure=SAMPLE_RESUME_PARSED,
        raw_text="Python backend engineer",
    )
    provider = MockAIProvider()
    analyzer = RecruiterLensAnalyzer(AIService(provider=provider), db_session)

    first = await analyzer.analyze(resume.id)
    second = await analyzer.analyze(resume.id)

    assert first["cached"] is False
    assert second["cached"] is True
    assert provider.call_count == 1
    assert first["scores"] == second["scores"]
    assert len(first["scores"]) == 5
    assert all(0 <= score["score"] <= 100 for score in first["scores"])
    assert first["attention_map"]


@pytest.mark.asyncio
async def test_recruiter_lens_endpoint_is_authenticated_and_structured(db_session) -> None:
    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session
    user = await UserRepository(db_session).create(
        email="recruiter-lens-endpoint@example.com",
        password_hash=hash_password("SecurePass123"),
    )
    resume = await ResumeRepository(db_session).create(
        user_id=user.id,
        title="Endpoint resume",
        parsed_structure=SAMPLE_RESUME_PARSED,
        raw_text="Python backend engineer",
    )
    await db_session.flush()
    token, _ = create_access_token(user.id)

    with patch("app.services.recruiter_lens_service.get_ai_service") as mock_get:
        mock_get.return_value = AIService(provider=MockAIProvider())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/resumes/{resume.id}/recruiter-lens",
                headers={"Authorization": f"Bearer {token}"},
            )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["recruiter_snapshot"]["target_role"]
    assert len(data["scores"]) == 5
    assert data["attention_map"]
    assert data["potentially_missed"]
    assert data["improvements"]

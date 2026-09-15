from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.client import AIService
from app.ai.providers.mock_provider import MockAIProvider
from app.ai.tasks.career_trajectory import CareerTrajectoryAnalyzer
from app.core.database import get_async_session
from app.core.security import create_access_token, hash_password
from app.main import app
from app.repositories import ResumeRepository, UserRepository
from tests.test_job_matching import SAMPLE_RESUME_PARSED


@pytest.mark.asyncio
async def test_trajectory_readiness_is_deterministic_and_cached(db_session) -> None:
    resume = await ResumeRepository(db_session).create(
        title="Trajectory test",
        parsed_structure=SAMPLE_RESUME_PARSED,
        raw_text="Python backend engineer",
    )
    provider = MockAIProvider()
    analyzer = CareerTrajectoryAnalyzer(AIService(provider=provider), db_session)

    first = await analyzer.analyze(resume.id)
    second = await analyzer.analyze(resume.id)

    assert first["cached"] is False
    assert second["cached"] is True
    assert provider.call_count == 1
    assert first["paths"] == second["paths"]
    assert sum(factor["weight"] for factor in first["paths"][0]["factors"]) == 100
    assert 0 <= first["paths"][0]["readiness_score"] <= 100


@pytest.mark.asyncio
async def test_trajectory_endpoint_returns_grounded_paths(db_session) -> None:
    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session
    user = await UserRepository(db_session).create(
        email="trajectory-endpoint@example.com",
        password_hash=hash_password("SecurePass123"),
    )
    resume = await ResumeRepository(db_session).create(
        user_id=user.id,
        title="Endpoint trajectory",
        parsed_structure=SAMPLE_RESUME_PARSED,
        raw_text="Python backend engineer",
    )
    await db_session.flush()
    token, _ = create_access_token(user.id)

    with patch("app.services.trajectory_service.get_ai_service") as mock_get:
        mock_get.return_value = AIService(provider=MockAIProvider())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/resumes/{resume.id}/trajectory",
                headers={"Authorization": f"Bearer {token}"},
            )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["current_profile"]
    assert data["paths"]
    assert "readiness_score" in data["paths"][0]
    assert "skill_gaps" in data["paths"][0]
    assert "proof_gaps" in data["paths"][0]

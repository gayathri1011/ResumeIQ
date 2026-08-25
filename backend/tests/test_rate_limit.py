"""Rate limiting tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core import rate_limit
from app.core.config import settings
from app.core.database import get_async_session
from app.main import app
from tests.fixtures.auth import auth_headers, signup_user


@pytest.fixture(autouse=True)
def reset_rate_limit_buckets() -> None:
    with rate_limit._lock:
        rate_limit._buckets.clear()
    yield
    with rate_limit._lock:
        rate_limit._buckets.clear()


@pytest.fixture
async def auth_client(db_session) -> AsyncClient:
    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_auth_rate_limit_returns_429_with_retry_after(auth_client: AsyncClient) -> None:
    original_limit = settings.auth_rate_limit_per_minute
    settings.auth_rate_limit_per_minute = 2
    try:
        for _ in range(2):
            response = await auth_client.post(
                "/api/v1/auth/login",
                json={"email": "missing@example.com", "password": "wrong"},
            )
            assert response.status_code in {401, 422}

        blocked = await auth_client.post(
            "/api/v1/auth/login",
            json={"email": "missing@example.com", "password": "wrong"},
        )
    finally:
        settings.auth_rate_limit_per_minute = original_limit

    assert blocked.status_code == 429
    body = blocked.json()
    assert body["error"]["code"] == "rate_limit_exceeded"
    assert blocked.headers.get("Retry-After") == "60"


@pytest.mark.asyncio
async def test_ai_rate_limit_returns_429(auth_client: AsyncClient, db_session) -> None:
    from app.models.enums import ResumeVersionSource, ResumeVersionStatus
    from app.repositories import ResumeRepository, ResumeVersionRepository
    from tests.test_job_matching import SAMPLE_RESUME_PARSED

    original_limit = settings.ai_rate_limit_per_minute
    settings.ai_rate_limit_per_minute = 1
    try:
        _, token = await signup_user(auth_client)
        user_response = await auth_client.get("/api/v1/auth/me", headers=auth_headers(token))
        user_id = user_response.json()["id"]

        resume_repo = ResumeRepository(db_session)
        version_repo = ResumeVersionRepository(db_session)
        resume = await resume_repo.create(
            user_id=user_id,
            title="Rate Limit Resume",
            parsed_structure=SAMPLE_RESUME_PARSED,
            raw_text="Python engineer",
        )
        await version_repo.create(
            resume_id=resume.id,
            version_number=1,
            label="Original",
            content_snapshot=SAMPLE_RESUME_PARSED,
            source=ResumeVersionSource.UPLOAD,
            status=ResumeVersionStatus.ACTIVE,
        )

        first = await auth_client.post(
            f"/api/v1/resumes/{resume.id}/analyze",
            headers=auth_headers(token),
        )
        assert first.status_code == 200

        second = await auth_client.post(
            f"/api/v1/resumes/{resume.id}/analyze",
            headers=auth_headers(token),
        )
    finally:
        settings.ai_rate_limit_per_minute = original_limit

    assert second.status_code == 429
    assert second.json()["error"]["code"] == "rate_limit_exceeded"

"""App-wide error handling and standardized response tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from pymongo.errors import ServerSelectionTimeoutError

from app.ai.errors import AIProviderError
from app.core.config import settings
from app.core.database import get_async_session
from app.main import app
from tests.fixtures.auth import auth_headers, signup_user


@pytest.mark.asyncio
async def test_app_error_envelope_shape() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/resumes/upload",
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )

    assert response.status_code in {400, 401}
    if response.status_code == 400:
        body = response.json()
        assert body["error"]["code"] == "invalid_file_type"
        assert "message" in body["error"]
        assert "details" in body["error"]


@pytest.mark.asyncio
async def test_unhandled_exception_returns_safe_message(auth_client: AsyncClient) -> None:
    _, token = await signup_user(auth_client)
    with patch(
        "app.services.resume_service.ResumeService.get_resume",
        new=AsyncMock(side_effect=RuntimeError("secret internal traceback details")),
    ):
        response = await auth_client.get(
            "/api/v1/resumes/00000000-0000-0000-0000-000000000001",
            headers=auth_headers(token),
        )

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "An unexpected error occurred."
    assert body["error"]["details"] is None


@pytest.mark.asyncio
async def test_validation_error_uses_standard_envelope() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/signup",
            json={"email": "not-an-email", "password": "short"},
        )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert "message" in body["error"]
    if not settings.debug:
        assert body["error"]["details"] is None


@pytest.mark.asyncio
async def test_database_unavailable_returns_degraded_message(auth_client: AsyncClient) -> None:
    _, token = await signup_user(auth_client)

    async def failing_session():
        raise ServerSelectionTimeoutError("connection refused")
        yield  # pragma: no cover

    app.dependency_overrides[get_async_session] = failing_session
    try:
        response = await auth_client.get("/api/v1/resumes", headers=auth_headers(token))
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "database_unavailable"
    assert "temporarily unavailable" in body["error"]["message"].lower()


@pytest.mark.asyncio
async def test_ai_provider_down_returns_friendly_error(auth_client: AsyncClient, db_session) -> None:
    from app.models.enums import ResumeVersionSource, ResumeVersionStatus
    from app.repositories import ResumeRepository, ResumeVersionRepository
    from tests.test_job_matching import SAMPLE_RESUME_PARSED

    _, token = await signup_user(auth_client)
    user_response = await auth_client.get("/api/v1/auth/me", headers=auth_headers(token))
    user_id = user_response.json()["id"]

    resume_repo = ResumeRepository(db_session)
    version_repo = ResumeVersionRepository(db_session)
    resume = await resume_repo.create(
        user_id=user_id,
        title="AI Failure Resume",
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

    with patch(
        "app.ai.client.AIService.complete_structured",
        new=AsyncMock(side_effect=AIProviderError()),
    ):
        response = await auth_client.post(
            f"/api/v1/resumes/{resume.id}/analyze",
            headers=auth_headers(token),
        )

    assert response.status_code == 502
    body = response.json()
    assert body["error"]["code"] == "ai_provider_error"
    assert "temporarily unavailable" in body["error"]["message"].lower()


@pytest.mark.asyncio
async def test_upload_requires_authentication() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/resumes/upload",
            files={"file": ("resume.pdf", b"%PDF-1.4", "application/pdf")},
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_upload_rejects_empty_file(auth_client: AsyncClient) -> None:
    _, token = await signup_user(auth_client)
    response = await auth_client.post(
        "/api/v1/resumes/upload",
        headers=auth_headers(token),
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "corrupted_file"


@pytest.mark.asyncio
async def test_signup_rejects_duplicate_email(auth_client: AsyncClient) -> None:
    email = "duplicate@example.com"
    first = await auth_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "SecurePass123", "full_name": "One"},
    )
    assert first.status_code == 200

    second = await auth_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "SecurePass123", "full_name": "Two"},
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "email_already_registered"

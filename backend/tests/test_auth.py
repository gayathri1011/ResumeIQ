"""Authentication tests."""

from __future__ import annotations

import copy
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_async_session
from app.core.security import hash_password, verify_password
from app.main import app
from app.repositories import ResumeRepository, ResumeVersionRepository, UserRepository
from app.models.enums import ResumeVersionSource, ResumeVersionStatus
from tests.test_job_matching import SAMPLE_RESUME_PARSED


@pytest.fixture
async def auth_client(db_session) -> AsyncClient:
    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


async def _signup(client: AsyncClient, email: str, password: str = "SecurePass123") -> str:
    response = await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_password_hashing_never_stores_plaintext() -> None:
    password = "SecurePass123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong-password", hashed)


@pytest.mark.asyncio
async def test_signup_login_logout_flow(auth_client: AsyncClient) -> None:
    email = f"user-{uuid4().hex[:8]}@example.com"
    signup = await auth_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "SecurePass123", "full_name": "Gayathri"},
    )
    assert signup.status_code == 200
    token = signup.json()["access_token"]
    assert signup.json()["user"]["email"] == email

    login = await auth_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePass123"},
    )
    assert login.status_code == 200
    assert login.json()["access_token"]

    me = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == email

    logout = await auth_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout.status_code == 200


@pytest.mark.asyncio
async def test_login_rejects_invalid_credentials(auth_client: AsyncClient) -> None:
    email = f"bad-{uuid4().hex[:8]}@example.com"
    await _signup(auth_client, email)

    response = await auth_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPassword1"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_protected_endpoint_rejects_unauthenticated(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/api/v1/resumes")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_expired_or_invalid_token_rejected(auth_client: AsyncClient) -> None:
    response = await auth_client.get(
        "/api/v1/resumes",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


@pytest.mark.asyncio
async def test_user_cannot_access_another_users_resume(auth_client: AsyncClient, db_session) -> None:
    user_a_token = await _signup(auth_client, f"a-{uuid4().hex[:8]}@example.com")
    user_b_token = await _signup(auth_client, f"b-{uuid4().hex[:8]}@example.com")

    user_repo = UserRepository(db_session)
    user_a = await user_repo.get_by_email((await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {user_a_token}"},
    )).json()["email"])

    resume_repo = ResumeRepository(db_session)
    version_repo = ResumeVersionRepository(db_session)
    resume = await resume_repo.create(
        user_id=user_a.id,
        title="Private Resume",
        parsed_structure=copy.deepcopy(SAMPLE_RESUME_PARSED),
    )
    await version_repo.create(
        resume_id=resume.id,
        version_number=1,
        label="Original",
        content_snapshot=copy.deepcopy(SAMPLE_RESUME_PARSED),
        source=ResumeVersionSource.UPLOAD,
        status=ResumeVersionStatus.ACTIVE,
    )

    blocked = await auth_client.get(
        f"/api/v1/resumes/{resume.id}",
        headers={"Authorization": f"Bearer {user_b_token}"},
    )
    assert blocked.status_code == 404
    assert blocked.json()["error"]["code"] == "resume_not_found"

    allowed = await auth_client.get(
        f"/api/v1/resumes/{resume.id}",
        headers={"Authorization": f"Bearer {user_a_token}"},
    )
    assert allowed.status_code == 200


@pytest.mark.asyncio
async def test_user_cannot_access_another_users_job(auth_client: AsyncClient, db_session) -> None:
    from app.repositories import JobDescriptionRepository

    user_a_token = await _signup(auth_client, f"ja-{uuid4().hex[:8]}@example.com")
    user_b_token = await _signup(auth_client, f"jb-{uuid4().hex[:8]}@example.com")

    user_repo = UserRepository(db_session)
    user_a = await user_repo.get_by_email((await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {user_a_token}"},
    )).json()["email"])

    job_repo = JobDescriptionRepository(db_session)
    job = await job_repo.create(
        user_id=user_a.id,
        title="Private JD",
        raw_text="A" * 200,
        parsed_requirements={"job_title": "Engineer"},
    )

    blocked = await auth_client.get(
        f"/api/v1/jobs/{job.id}",
        headers={"Authorization": f"Bearer {user_b_token}"},
    )
    assert blocked.status_code == 404
    assert blocked.json()["error"]["code"] == "job_not_found"

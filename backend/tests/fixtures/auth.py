"""Shared auth helpers for API tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_async_session
from app.main import app


@pytest.fixture
async def auth_client(db_session) -> AsyncClient:
    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


async def signup_user(
    client: AsyncClient,
    *,
    email: str | None = None,
    password: str = "SecurePass123",
    full_name: str = "Test User",
) -> tuple[str, str]:
    address = email or f"user-{uuid4().hex[:8]}@example.com"
    response = await client.post(
        "/api/v1/auth/signup",
        json={"email": address, "password": password, "full_name": full_name},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return address, token


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}

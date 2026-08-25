"""Integration tests for resume upload with database persistence."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from app.core.database import MongoSession, get_async_session
from app.main import app
from app.repositories import ResumeRepository


@pytest.mark.asyncio
async def test_upload_persists_resume(sample_pdf, db_session: MongoSession) -> None:
    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session

    content = sample_pdf.read_bytes()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/resumes/upload",
            files={"file": ("sample_resume.pdf", content, "application/pdf")},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "sample_resume"
    assert "experience" in data["sections_found"]
    assert "certifications" in data["sections_missing"]

    repo = ResumeRepository(db_session)
    resume = await repo.get_by_id(data["id"])
    assert resume is not None
    assert resume.parsed_structure is not None
    assert resume.parsed_structure.get("experience") is not None
    assert resume.raw_text is not None
    assert "Jane Doe" in resume.raw_text

    await db_session.commit()

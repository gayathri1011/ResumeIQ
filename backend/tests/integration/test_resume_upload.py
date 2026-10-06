"""Integration tests for resume upload with database persistence."""

from __future__ import annotations

import pytest
from app.core.database import MongoSession
from app.repositories import ResumeRepository
from tests.fixtures.auth import auth_headers, signup_user


@pytest.mark.asyncio
async def test_upload_persists_resume(sample_pdf, auth_client, db_session: MongoSession) -> None:
    content = sample_pdf.read_bytes()
    _, token = await signup_user(auth_client)
    response = await auth_client.post(
        "/api/v1/resumes/upload",
        headers=auth_headers(token),
        files={"file": ("sample_resume.pdf", content, "application/pdf")},
    )

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

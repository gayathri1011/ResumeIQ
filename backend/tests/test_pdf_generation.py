"""Tests for resume PDF generation."""

from __future__ import annotations

import copy
from unittest.mock import patch

import pymupdf as fitz
import pytest

from app.core.exceptions import AppError
from app.pdf.html_renderer import render_resume_html
from app.pdf.pdf_generator import generate_resume_pdf
from app.pdf.template_context import build_template_context
from app.services.pdf_service import PdfService
from tests.test_job_matching import SAMPLE_RESUME_PARSED
from app.core.security import hash_password

COMPLETE_RESUME_PARSED = {
    "personal_information": {
        "name": "Jane Doe",
        "email": "jane.doe@example.com",
        "phone": "+1 555-010-2000",
        "location": "Boston, MA",
    },
    "professional_summary": (
        "Software engineer with 5 years of experience building scalable backend systems."
    ),
    "education": [
        {
            "title": "B.S. Computer Science",
            "organization": "State University",
            "date_range": "2016 – 2020",
            "description": None,
        }
    ],
    "experience": [
        {
            "title": "Senior Software Engineer",
            "organization": "Tech Co",
            "date_range": "2020 – Present",
            "description": "• Built backend services with Python and PostgreSQL.\n• Led API design for internal platforms.",
        }
    ],
    "projects": [
        {
            "title": "API Platform",
            "description": "FastAPI microservices project serving internal teams.",
        }
    ],
    "skills": ["Python", "SQL", "REST APIs", "FastAPI"],
    "certifications": [
        {
            "title": "AWS Certified Developer",
            "organization": "Amazon Web Services",
            "date_range": "2023",
            "description": None,
        }
    ],
    "achievements": ["Employee of the Year 2022"],
    "links": [{"type": "linkedin", "url": "https://linkedin.com/in/janedoe"}],
    "_meta": {
        "sections_found": [
            "personal_information",
            "professional_summary",
            "education",
            "experience",
            "projects",
            "skills",
            "certifications",
            "achievements",
            "links",
        ],
        "sections_missing": [],
    },
}

SPARSE_RESUME_PARSED = {
    "personal_information": {"name": "Alex Kim", "email": "alex@example.com"},
    "professional_summary": "Early-career software developer.",
    "experience": [
        {
            "title": "Junior Developer",
            "organization": "Startup Inc",
            "date_range": "2024 – Present",
            "description": "Shipped product features in a small team.",
        }
    ],
    "skills": ["JavaScript", "React"],
    "_meta": {"sections_found": ["experience", "skills"], "sections_missing": ["certifications"]},
}


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        text = "\n".join(page.get_text() for page in doc)
        # PyMuPDF may extract ligatures (e.g. "fi" -> single glyph); normalize for assertions.
        return text.replace("\ufb01", "fi").replace("\ufb00", "ff").replace("\ufb02", "fl")
    finally:
        doc.close()


def test_generate_pdf_with_complete_data() -> None:
    pdf_bytes = generate_resume_pdf(COMPLETE_RESUME_PARSED)
    assert pdf_bytes.startswith(b"%PDF")

    text = _extract_pdf_text(pdf_bytes)
    assert "Jane Doe" in text
    assert "Professional Summary" in text
    assert "Senior Software Engineer" in text
    assert "AWS Certified Developer" in text
    assert "Employee of the Year 2022" in text
    assert "linkedin.com/in/janedoe" in text.lower()


def test_generate_pdf_with_sparse_data_omits_empty_sections() -> None:
    pdf_bytes = generate_resume_pdf(SPARSE_RESUME_PARSED)
    text = _extract_pdf_text(pdf_bytes)

    assert "Alex Kim" in text
    assert "Junior Developer" in text
    assert "Certifications" not in text
    assert "Achievements" not in text
    assert "Projects" not in text


def test_pdf_reflects_current_version_content() -> None:
    before = generate_resume_pdf(COMPLETE_RESUME_PARSED)
    before_text = _extract_pdf_text(before)
    assert "Senior Software Engineer" in before_text

    updated = copy.deepcopy(COMPLETE_RESUME_PARSED)
    updated["experience"][0]["title"] = "Staff Software Engineer"
    after = generate_resume_pdf(updated)
    after_text = _extract_pdf_text(after)

    assert "Staff Software Engineer" in after_text
    assert "Senior Software Engineer" not in after_text


def test_sparse_template_context_omits_empty_headings() -> None:
    context = build_template_context(SPARSE_RESUME_PARSED)
    assert context["certifications"] == []
    assert context["achievements"] == []
    assert context["projects"] == []

    html = render_resume_html(SPARSE_RESUME_PARSED)
    assert "Certifications" not in html
    assert "Achievements" not in html


def test_generate_pdf_surfaces_rendering_failure() -> None:
    with patch("app.pdf.pdf_generator.fitz.Story", side_effect=RuntimeError("render failed")):
        with pytest.raises(AppError) as exc:
            generate_resume_pdf(COMPLETE_RESUME_PARSED)
    assert exc.value.code == "pdf_generation_failed"


@pytest.mark.asyncio
async def test_generate_version_pdf_service(db_session) -> None:
    from uuid import uuid4

    from app.models.enums import ResumeVersionSource, ResumeVersionStatus
    from app.repositories import ResumeRepository, ResumeVersionRepository, UserRepository

    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        email=f"pdf-svc-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("SecurePass123"),
        full_name="PDF Service User",
    )
    resume_repo = ResumeRepository(db_session)
    version_repo = ResumeVersionRepository(db_session)
    service = PdfService(db_session)

    resume = await resume_repo.create(
        user_id=user.id,
        title="PDF Export",
        parsed_structure=copy.deepcopy(COMPLETE_RESUME_PARSED),
    )
    version = await version_repo.create(
        resume_id=resume.id,
        version_number=1,
        label="Software Engineer Resume",
        source=ResumeVersionSource.UPLOAD,
        status=ResumeVersionStatus.ACTIVE,
        content_snapshot=copy.deepcopy(COMPLETE_RESUME_PARSED),
    )

    pdf_bytes, filename = await service.generate_version_pdf(
        resume.id,
        version.id,
        user_id=resume.user_id,
    )
    assert filename == "software-engineer-resume.pdf"
    assert pdf_bytes.startswith(b"%PDF")
    assert "Jane Doe" in _extract_pdf_text(pdf_bytes)


@pytest.mark.asyncio
async def test_generate_version_pdf_endpoint(db_session) -> None:
    from uuid import uuid4

    from httpx import ASGITransport, AsyncClient

    from app.core.database import get_async_session
    from app.main import app
    from app.models.enums import ResumeVersionSource, ResumeVersionStatus
    from app.repositories import ResumeRepository, ResumeVersionRepository

    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            auth = await client.post(
                "/api/v1/auth/signup",
                json={
                    "email": f"pdf-api-{uuid4().hex[:8]}@example.com",
                    "password": "SecurePass123",
                    "full_name": "PDF API User",
                },
            )
            assert auth.status_code == 200
            token = auth.json()["access_token"]
            authed_user_id = auth.json()["user"]["id"]

            resume_repo = ResumeRepository(db_session)
            version_repo = ResumeVersionRepository(db_session)
            resume = await resume_repo.create(
                user_id=authed_user_id,
                title="PDF API Authed",
                parsed_structure=copy.deepcopy(SAMPLE_RESUME_PARSED),
            )
            version = await version_repo.create(
                resume_id=resume.id,
                version_number=1,
                label="Data Analyst Resume",
                source=ResumeVersionSource.UPLOAD,
                status=ResumeVersionStatus.ACTIVE,
                content_snapshot=copy.deepcopy(SAMPLE_RESUME_PARSED),
            )

            response = await client.post(
                f"/api/v1/resumes/{resume.id}/versions/{version.id}/generate",
                headers={"Authorization": f"Bearer {token}"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "data-analyst-resume.pdf" in response.headers.get("content-disposition", "")
    assert response.content.startswith(b"%PDF")

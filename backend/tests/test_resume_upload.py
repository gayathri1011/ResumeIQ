"""Tests for resume upload validation and parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import settings
from app.core.upload_errors import EmptyResumeError, FileTooLargeError, InvalidFileTypeError
from app.parsers.registry import parse_resume_file
from app.services.resume_service import ResumeService
from tests.fixtures.auth import auth_headers, signup_user


class TestResumeParser:
    def test_pdf_extraction(self, sample_pdf: Path) -> None:
        result = parse_resume_file(sample_pdf, "sample_resume.pdf", "application/pdf")
        assert "Jane Doe" in result.raw_text
        assert result.structured.experience is not None
        assert len(result.structured.experience) >= 1
        assert result.structured.skills is not None
        assert "Python" in result.structured.skills
        assert "experience" in result.structured.meta.sections_found

    def test_docx_extraction(self, sample_docx: Path) -> None:
        result = parse_resume_file(sample_docx, "sample_resume.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        assert "Jane Doe" in result.raw_text
        assert result.structured.education is not None
        assert "certifications" in result.structured.meta.sections_missing

    def test_missing_section_not_fabricated(self, sample_pdf: Path) -> None:
        result = parse_resume_file(sample_pdf, "sample_resume.pdf", "application/pdf")
        assert result.structured.certifications is None
        assert "certifications" in result.structured.meta.sections_missing

    def test_corrupted_pdf_raises(self, corrupted_pdf: Path) -> None:
        from app.core.upload_errors import CorruptedFileError

        with pytest.raises((CorruptedFileError, EmptyResumeError)):
            parse_resume_file(corrupted_pdf, "corrupted.pdf", "application/pdf")

    def test_empty_pdf_raises(self, empty_pdf: Path) -> None:
        with pytest.raises(EmptyResumeError):
            parse_resume_file(empty_pdf, "empty.pdf", "application/pdf")

    def test_invalid_extension_raises(self, sample_pdf: Path) -> None:
        with pytest.raises(InvalidFileTypeError):
            parse_resume_file(sample_pdf, "resume.txt", "text/plain")


class TestResumeServiceValidation:
    def test_validate_rejects_invalid_type(self) -> None:
        service = ResumeService(session=None)  # type: ignore[arg-type]
        with pytest.raises(InvalidFileTypeError):
            service._validate_upload("resume.txt", "text/plain", 100)

    def test_validate_rejects_oversized_file(self) -> None:
        service = ResumeService(session=None)  # type: ignore[arg-type]
        with pytest.raises(FileTooLargeError):
            service._validate_upload(
                "resume.pdf",
                "application/pdf",
                settings.upload_max_size_bytes + 1,
            )


@pytest.mark.asyncio
async def test_upload_endpoint_rejects_invalid_type(auth_client) -> None:
    _, token = await signup_user(auth_client)
    response = await auth_client.post(
        "/api/v1/resumes/upload",
        headers=auth_headers(token),
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_file_type"


@pytest.mark.asyncio
async def test_upload_endpoint_rejects_oversized_file(auth_client) -> None:
    _, token = await signup_user(auth_client)
    oversized = b"x" * (settings.upload_max_size_bytes + 1)
    response = await auth_client.post(
        "/api/v1/resumes/upload",
        headers=auth_headers(token),
        files={"file": ("big.pdf", oversized, "application/pdf")},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


@pytest.mark.asyncio
async def test_upload_endpoint_rejects_corrupted_pdf(auth_client, corrupted_pdf: Path) -> None:
    _, token = await signup_user(auth_client)
    content = corrupted_pdf.read_bytes()
    response = await auth_client.post(
        "/api/v1/resumes/upload",
        headers=auth_headers(token),
        files={"file": ("corrupted.pdf", content, "application/pdf")},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] in {"corrupted_file", "empty_resume", "extraction_failed"}

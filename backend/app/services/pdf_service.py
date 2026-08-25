"""Resume PDF generation service."""

from __future__ import annotations

import asyncio
from uuid import UUID

from app.core.database import MongoSession

from app.core.exceptions import AppError
from app.pdf.pdf_generator import generate_resume_pdf
from app.pdf.template_context import sanitize_filename
from app.repositories import ResumeRepository, ResumeVersionRepository
from app.utils.ownership import require_owned_resume
from app.utils.version_content import get_version_content


class PdfService:
    """Generates downloadable PDFs from persisted resume version content."""

    def __init__(self, session: MongoSession) -> None:
        self.session = session
        self.resume_repo = ResumeRepository(session)
        self.version_repo = ResumeVersionRepository(session)

    async def generate_version_pdf(
        self,
        resume_id: UUID,
        version_id: UUID,
        *,
        user_id: UUID,
    ) -> tuple[bytes, str]:
        await require_owned_resume(self.resume_repo, resume_id, user_id)

        version = await self.version_repo.get_by_resume_and_id(resume_id, version_id)
        if version is None:
            raise AppError(
                "Resume version not found.",
                code="resume_version_not_found",
                status_code=404,
            )

        content = get_version_content(version)
        if not any(
            content.get(key)
            for key in (
                "personal_information",
                "professional_summary",
                "education",
                "experience",
                "projects",
                "skills",
                "certifications",
                "achievements",
                "links",
            )
        ):
            raise AppError(
                "This version has no resume content to export.",
                code="resume_not_parsed",
                status_code=422,
            )

        pdf_bytes = await asyncio.to_thread(generate_resume_pdf, content)
        filename = f"{sanitize_filename(version.label, fallback='resume')}.pdf"
        return pdf_bytes, filename

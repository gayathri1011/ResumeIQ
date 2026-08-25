"""Business logic orchestration — implemented in feature phases."""

from __future__ import annotations

import asyncio
import logging
import tempfile
import uuid
from pathlib import Path

from fastapi import UploadFile
from app.core.database import MongoSession

from app.core.config import settings
from app.core.upload_errors import (
    CorruptedFileError,
    EmptyResumeError,
    ExtractionFailedError,
    FileTooLargeError,
    InvalidFileTypeError,
)
from app.models.enums import ResumeVersionSource, ResumeVersionStatus
from app.parsers.registry import parse_resume_file
from app.repositories import ResumeRepository, ResumeVersionRepository, UserRepository
from app.schemas.resume import ResumeUploadResponse
from app.utils.file_storage import get_file_storage
from app.utils.ownership import require_owned_resume
from app.utils.version_create import create_resume_version

logger = logging.getLogger(__name__)


class ResumeService:
    """Orchestrates resume CRUD and upload/parsing workflows."""

    def __init__(self, session: MongoSession) -> None:
        self.session = session
        self.resume_repo = ResumeRepository(session)
        self.version_repo = ResumeVersionRepository(session)
        self.user_repo = UserRepository(session)
        self.storage = get_file_storage()

    def _validate_upload(self, filename: str, content_type: str | None, size: int) -> None:
        extension = Path(filename).suffix.lower().lstrip(".")
        allowed_extensions = settings.upload_allowed_extensions_list

        if extension not in allowed_extensions:
            raise InvalidFileTypeError()

        if content_type and content_type not in settings.upload_allowed_mime_types:
            if content_type != "application/octet-stream":
                raise InvalidFileTypeError(
                    "Unsupported file type. Please upload a PDF, DOCX, or image resume (PNG, JPG, WEBP).",
                )

        if size > settings.upload_max_size_bytes:
            raise FileTooLargeError(settings.upload_max_size_mb)

        if size == 0:
            raise CorruptedFileError("The uploaded file is empty.")

    async def upload_resume(self, upload: UploadFile, *, user_id: uuid.UUID) -> ResumeUploadResponse:
        filename = upload.filename or "resume"
        content = await upload.read()
        content_type = upload.content_type

        self._validate_upload(filename, content_type, len(content))

        suffix = Path(filename).suffix.lower()
        tmp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)

            parsed_doc = await asyncio.to_thread(
                parse_resume_file,
                tmp_path,
                filename,
                content_type,
            )
        except (CorruptedFileError, EmptyResumeError, ExtractionFailedError, InvalidFileTypeError):
            raise
        except Exception as exc:
            raise ExtractionFailedError() from exc
        finally:
            if tmp_path is not None:
                try:
                    tmp_path.unlink(missing_ok=True)
                except OSError:
                    pass

        title = Path(filename).stem or "Untitled Resume"

        structured = parsed_doc.structured
        structured.meta.file_size_bytes = len(content)
        parsed_dict = structured.to_storage_dict()

        resume = await self.resume_repo.create(
            user_id=user_id,
            title=title,
            original_filename=filename,
            mime_type=content_type,
            raw_text=parsed_doc.raw_text,
            parsed_structure=parsed_dict,
            is_active=True,
        )

        storage_path = await self.storage.save_resume_file(
            content=content,
            original_filename=filename,
            resume_id=resume.id,
        )
        resume.file_path = storage_path
        await self.session.flush()

        await create_resume_version(
            self.session,
            resume_id=resume.id,
            label="Master Resume",
            content_snapshot=parsed_dict,
            raw_text=parsed_doc.raw_text,
            source=ResumeVersionSource.UPLOAD,
            status=ResumeVersionStatus.ACTIVE,
            is_master=True,
        )

        from app.ai.client import get_ai_service
        from app.services.embedding_service import EmbeddingService

        try:
            await EmbeddingService(get_ai_service(), self.session).ensure_resume_embedding(resume)
        except Exception as exc:
            logger.warning(
                "Embedding generation skipped during upload for resume %s: %s",
                resume.id,
                exc,
            )

        return ResumeUploadResponse(
            id=resume.id,
            title=resume.title,
            original_filename=resume.original_filename,
            file_size_bytes=len(content),
            mime_type=resume.mime_type,
            sections_found=structured.meta.sections_found,
            sections_missing=structured.meta.sections_missing,
            created_at=resume.created_at,
        )

    async def get_resume(self, resume_id: uuid.UUID, *, user_id: uuid.UUID):
        return await require_owned_resume(self.resume_repo, resume_id, user_id)

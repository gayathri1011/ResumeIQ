"""Orchestrates bullet point improvement workflows."""

from __future__ import annotations

from uuid import UUID

from app.core.database import MongoSession

from app.ai.client import get_ai_service
from app.ai.tasks.bullet_improver import BulletPointImprover
from app.core.exceptions import AppError
from app.repositories import ResumeRepository, ResumeVersionRepository
from app.services.embedding_service import EmbeddingService
from app.utils.bullet_utils import (
    build_resume_context,
    list_resume_bullets,
    replace_resume_bullet,
)
from app.utils.ownership import require_owned_resume
from app.utils.resume_staleness import invalidate_resume_content_meta
from app.utils.version_content import (
    get_version_content,
    resolve_version,
    sync_resume_from_version,
    sync_version_content,
)


class BulletService:
    """Orchestrates bullet improvement and replace workflows."""

    def __init__(self, session: MongoSession) -> None:
        self.session = session
        self.resume_repo = ResumeRepository(session)
        self.version_repo = ResumeVersionRepository(session)

    async def list_bullets(
        self,
        resume_id: UUID,
        *,
        user_id: UUID,
        resume_version_id: UUID | None = None,
    ) -> list[dict]:
        await require_owned_resume(self.resume_repo, resume_id, user_id)

        version = await resolve_version(
            self.version_repo,
            resume_id,
            version_id=resume_version_id,
        )
        content = get_version_content(version)  # type: ignore[arg-type]
        return list_resume_bullets(content)

    async def improve_bullet(
        self,
        bullet_text: str,
        *,
        resume_id: UUID | None = None,
        user_id: UUID | None = None,
        resume_version_id: UUID | None = None,
        target_role: str | None = None,
        regenerate: bool = False,
        previous_improved_text: str | None = None,
    ) -> dict:
        resume_context = ""
        if resume_id is not None:
            if user_id is None:
                raise AppError("Authentication required.", code="unauthorized", status_code=401)
            resume = await require_owned_resume(self.resume_repo, resume_id, user_id)
            version = await resolve_version(
                self.version_repo,
                resume_id,
                version_id=resume_version_id,
            )
            content = get_version_content(version)  # type: ignore[arg-type]
            resume_context = build_resume_context(content, version.raw_text or resume.raw_text)

        improver = BulletPointImprover(get_ai_service())
        return await improver.improve(
            bullet_text,
            resume_context=resume_context,
            target_role=target_role,
            regenerate=regenerate,
            previous_improved_text=previous_improved_text,
        )

    async def replace_bullet(
        self,
        *,
        resume_id: UUID,
        section: str,
        entry_index: int,
        bullet_index: int,
        improved_text: str,
        user_id: UUID,
        resume_version_id: UUID | None = None,
    ) -> dict:
        resume = await require_owned_resume(self.resume_repo, resume_id, user_id)

        version = await resolve_version(
            self.version_repo,
            resume_id,
            version_id=resume_version_id,
        )
        content = get_version_content(version)  # type: ignore[arg-type]

        updated_structure = replace_resume_bullet(
            content,
            section=section,  # type: ignore[arg-type]
            entry_index=entry_index,
            bullet_index=bullet_index,
            new_text=improved_text,
        )
        updated_structure = invalidate_resume_content_meta(updated_structure)

        await sync_version_content(self.version_repo, version, updated_structure)
        await sync_resume_from_version(self.resume_repo, resume, version)

        try:
            await EmbeddingService(get_ai_service(), self.session).ensure_resume_embedding(
                resume,
                resume_version=version,
            )
        except Exception:
            pass

        return {
            "resume_id": resume_id,
            "section": section,
            "entry_index": entry_index,
            "bullet_index": bullet_index,
            "updated_text": improved_text.strip(),
            "message": "Bullet updated in your saved resume.",
        }

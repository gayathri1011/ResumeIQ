"""Embedding generation and vector similarity helpers."""

from __future__ import annotations

import json
import math
from typing import Any
from uuid import UUID

from app.core.database import MongoSession

from app.ai.client import AIService
from app.ai.utils import hash_resume_content
from app.core.config import settings
from app.core.exceptions import AppError
from app.models.resume import Resume, ResumeVersion
from app.repositories import ResumeRepository, ResumeVersionRepository


def build_resume_embedding_text(
    parsed_structure: dict[str, Any] | None,
    raw_text: str | None,
) -> str:
    """Build text for embedding from parsed structure with raw text fallback."""
    if parsed_structure:
        content = {k: v for k, v in parsed_structure.items() if k != "_meta"}
        if content:
            return json.dumps(content, default=str)
    return (raw_text or "").strip()


def cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    """Cosine similarity in [-1, 1]; 1 means identical direction."""
    if len(vector_a) != len(vector_b) or not vector_a:
        return 0.0

    dot = sum(a * b for a, b in zip(vector_a, vector_b, strict=True))
    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def semantic_similarity_score(vector_a: list[float], vector_b: list[float]) -> float:
    """Map cosine similarity to a 0–100 score."""
    similarity = cosine_similarity(vector_a, vector_b)
    return max(0.0, min(100.0, ((similarity + 1.0) / 2.0) * 100.0))


class EmbeddingService:
    """Ensures resume embeddings exist and stay in sync with parsed content."""

    def __init__(self, ai_service: AIService, session: MongoSession) -> None:
        self.ai_service = ai_service
        self.session = session
        self.resume_repo = ResumeRepository(session)
        self.version_repo = ResumeVersionRepository(session)

    async def ensure_resume_embedding(
        self,
        resume: Resume,
        *,
        resume_version: ResumeVersion | None = None,
    ) -> list[float]:
        parsed = (
            resume_version.content_snapshot
            if resume_version and resume_version.content_snapshot
            else resume.parsed_structure
        )
        raw_text = resume_version.raw_text if resume_version else resume.raw_text

        if not parsed and not raw_text:
            raise AppError(
                "Resume has no parsed content to embed.",
                code="resume_not_parsed",
                status_code=422,
            )

        content_hash = hash_resume_content(parsed)
        embedding_text = build_resume_embedding_text(parsed, raw_text)
        if not embedding_text:
            raise AppError(
                "Resume has no content to embed.",
                code="resume_empty",
                status_code=422,
            )

        target = resume_version if resume_version else resume
        stored_hash = self._get_stored_embedding_hash(parsed)

        if (
            target.content_embedding is not None
            and stored_hash == content_hash
            and len(target.content_embedding) == settings.embedding_dimensions
        ):
            return list(target.content_embedding)

        embedding = await self.ai_service.embed(embedding_text[:8000])
        if len(embedding) != settings.embedding_dimensions:
            raise AppError(
                "Embedding generation returned an unexpected vector size.",
                code="embedding_invalid",
                status_code=502,
            )

        updated_parsed = dict(parsed or {})
        meta = dict(updated_parsed.get("_meta") or {})
        meta["embedding_content_hash"] = content_hash
        updated_parsed["_meta"] = meta

        if resume_version:
            await self.version_repo.update(
                resume_version,
                content_embedding=embedding,
                content_snapshot=updated_parsed,
            )
            await self.resume_repo.update(
                resume,
                content_embedding=embedding,
                parsed_structure=updated_parsed,
            )
        else:
            await self.resume_repo.update(
                resume,
                content_embedding=embedding,
                parsed_structure=updated_parsed,
            )
            active_version = await self._get_active_version(resume.id)
            if active_version:
                await self.version_repo.update(
                    active_version,
                    content_embedding=embedding,
                    content_snapshot=updated_parsed,
                )

        return embedding

    async def _get_active_version(self, resume_id: UUID) -> ResumeVersion | None:
        versions = await self.version_repo.list_by_resume(resume_id, limit=1)
        return versions[0] if versions else None

    def _get_stored_embedding_hash(self, parsed: dict[str, Any] | None) -> str | None:
        if not parsed:
            return None
        return (parsed.get("_meta") or {}).get("embedding_content_hash")

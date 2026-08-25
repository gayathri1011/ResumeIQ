"""Detect stale analysis/match data after resume content changes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.ai.utils import hash_resume_content
from app.core.database import MongoSession
from app.models.analysis import AIAnalysisResult
from app.repositories import AIAnalysisResultRepository, JobMatchRepository, ResumeAnalysisRepository


def invalidate_resume_content_meta(parsed_structure: dict[str, Any] | None) -> dict[str, Any]:
    """Clear embedding cache markers and stamp content update time."""
    if not parsed_structure:
        return {}
    updated = dict(parsed_structure)
    meta = dict(updated.get("_meta") or {})
    meta.pop("embedding_content_hash", None)
    meta["content_updated_at"] = datetime.now(UTC).isoformat()
    updated["_meta"] = meta
    return updated


async def compute_resume_staleness(
    session: MongoSession,
    *,
    resume_id: UUID,
    parsed_structure: dict[str, Any] | None,
    resume_version_id: UUID | None = None,
) -> dict[str, bool]:
    """Compare current content hash against analysis and match records."""
    current_hash = hash_resume_content(parsed_structure)
    analysis_stale = False
    match_stale = False

    analysis_repo = ResumeAnalysisRepository(session)
    if resume_version_id:
        analyses = await analysis_repo.list_by_resume(resume_id, limit=20)
        latest_analysis = next(
            (
                analysis
                for analysis in analyses
                if analysis.resume_version_id == resume_version_id
                and analysis.status.value == "completed"
            ),
            None,
        )
    else:
        latest_analysis = await analysis_repo.get_latest_by_resume(resume_id)

    if latest_analysis and latest_analysis.status.value == "completed":
        linked = await _get_linked_analysis_ai_result(session, latest_analysis.id)
        if linked and linked.input_hash != current_hash:
            analysis_stale = True

    match_repo = JobMatchRepository(session)
    matches = await match_repo.list_by_resume(resume_id, limit=20)
    for match in matches:
        if resume_version_id and match.resume_version_id != resume_version_id:
            continue
        meta = (match.breakdown or {}).get("_meta") or {}
        match_hash = meta.get("resume_content_hash")
        if match_hash and match_hash != current_hash:
            match_stale = True
            break

    return {
        "analysis_stale": analysis_stale,
        "match_stale": match_stale,
        "content_hash": current_hash,
    }


async def _get_linked_analysis_ai_result(
    session: MongoSession,
    analysis_id: UUID,
) -> AIAnalysisResult | None:
    return await AIAnalysisResultRepository(session).get_by_resume_analysis_id(analysis_id)

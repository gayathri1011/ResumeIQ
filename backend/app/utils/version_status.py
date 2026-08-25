"""Compute display status for resume versions."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.ai.utils import hash_resume_content
from app.core.database import MongoSession
from app.models.analysis import AIAnalysisResult
from app.models.enums import ResumeVersionSource, ResumeVersionStatus
from app.models.resume import ResumeVersion
from app.repositories import AIAnalysisResultRepository, JobMatchRepository, ResumeAnalysisRepository


def _status_from_version_context(
    version: ResumeVersion,
    *,
    latest_analysis: Any | None,
    linked_input_hash: str | None,
    latest_match: Any | None,
) -> dict[str, Any]:
    content_hash = hash_resume_content(version.content_snapshot)
    analysis_stale = False
    if latest_analysis and linked_input_hash and linked_input_hash != content_hash:
        analysis_stale = True

    match_stale = False
    if latest_match:
        meta = (latest_match.breakdown or {}).get("_meta") or {}
        match_hash = meta.get("resume_content_hash")
        if match_hash and match_hash != content_hash:
            match_stale = True

    status_key = "not_analyzed"
    status_label = "Not analyzed"

    if version.status == ResumeVersionStatus.DRAFT and version.source == ResumeVersionSource.OPTIMIZATION:
        status_key = "optimized"
        status_label = "Optimized (draft)"
    elif analysis_stale or match_stale:
        status_key = "needs_reanalysis"
        status_label = "Needs re-analysis"
    elif latest_analysis:
        status_key = "analyzed"
        status_label = "Analyzed"

    return {
        "status_key": status_key,
        "status_label": status_label,
        "overall_score": latest_analysis.overall_score if latest_analysis else version.overall_score,
        "analysis_stale": analysis_stale,
        "match_stale": match_stale,
        "reanalyze_recommended": analysis_stale or match_stale,
        "latest_match_score": latest_match.match_score if latest_match else None,
        "latest_match_job_title": None,
        "latest_match_company": None,
        "latest_match_id": latest_match.id if latest_match else None,
    }


async def compute_versions_status_batch(
    session: MongoSession,
    versions: list[ResumeVersion],
) -> dict[UUID, dict[str, Any]]:
    """Compute version status for many versions with shared DB reads."""
    if not versions:
        return {}

    resume_id = versions[0].resume_id
    analysis_repo = ResumeAnalysisRepository(session)
    match_repo = JobMatchRepository(session)
    analyses = await analysis_repo.list_by_resume(resume_id, limit=100)
    matches = await match_repo.list_by_resume(resume_id, limit=100)

    completed_ids = [
        analysis.id
        for analysis in analyses
        if analysis.status.value == "completed"
    ]
    linked_by_analysis: dict[UUID, AIAnalysisResult] = {}
    if completed_ids:
        linked_results = await AIAnalysisResultRepository(session).get_by_resume_analysis_ids(
            completed_ids
        )
        for linked in linked_results:
            if linked.resume_analysis_id is not None:
                linked_by_analysis[linked.resume_analysis_id] = linked

    latest_analysis_by_version: dict[UUID, Any] = {}
    for analysis in analyses:
        if analysis.status.value != "completed":
            continue
        if analysis.resume_version_id is None:
            continue
        if analysis.resume_version_id not in latest_analysis_by_version:
            latest_analysis_by_version[analysis.resume_version_id] = analysis

    latest_match_by_version: dict[UUID, Any] = {}
    for match in matches:
        if match.resume_version_id is None:
            continue
        if match.resume_version_id not in latest_match_by_version:
            latest_match_by_version[match.resume_version_id] = match

    outcomes: dict[UUID, dict[str, Any]] = {}
    for version in versions:
        latest_analysis = latest_analysis_by_version.get(version.id)
        linked = (
            linked_by_analysis.get(latest_analysis.id)
            if latest_analysis is not None
            else None
        )
        outcomes[version.id] = _status_from_version_context(
            version,
            latest_analysis=latest_analysis,
            linked_input_hash=linked.input_hash if linked else None,
            latest_match=latest_match_by_version.get(version.id),
        )
    return outcomes


async def compute_version_status(
    session: MongoSession,
    version: ResumeVersion,
) -> dict[str, Any]:
    batch = await compute_versions_status_batch(session, [version])
    return batch[version.id]

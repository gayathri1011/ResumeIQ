"""Orchestrates resume analysis workflows."""

from __future__ import annotations

from uuid import UUID

from app.ai.client import get_ai_service
from app.ai.tasks.resume_analyzer import ResumeAnalyzer
from app.core.database import MongoSession
from app.core.exceptions import AppError
from app.models.analysis import AIAnalysisResult
from app.repositories import (
    AIAnalysisResultRepository,
    ResumeAnalysisRepository,
    ResumeRepository,
    ResumeVersionRepository,
)
from app.utils.ownership import require_owned_resume
from app.utils.resume_staleness import compute_resume_staleness
from app.utils.version_content import resolve_version, sync_resume_from_version


class AnalysisService:
    """Orchestrates resume analysis workflows."""

    def __init__(self, session: MongoSession) -> None:
        self.session = session
        self.resume_repo = ResumeRepository(session)
        self.analysis_repo = ResumeAnalysisRepository(session)
        self.version_repo = ResumeVersionRepository(session)

    async def analyze_resume(
        self,
        resume_id: UUID,
        *,
        user_id: UUID,
        resume_version_id: UUID | None = None,
    ) -> dict:
        await require_owned_resume(self.resume_repo, resume_id, user_id)

        analyzer = ResumeAnalyzer(get_ai_service(), self.session)
        return await analyzer.analyze(resume_id, resume_version_id=resume_version_id)

    async def get_resume_with_analysis(
        self,
        resume_id: UUID,
        *,
        user_id: UUID,
        resume_version_id: UUID | None = None,
    ) -> dict:
        resume = await require_owned_resume(self.resume_repo, resume_id, user_id)

        version = await resolve_version(
            self.version_repo,
            resume_id,
            version_id=resume_version_id,
            required=False,
        )
        if version and version.content_snapshot:
            resume = await sync_resume_from_version(self.resume_repo, resume, version)

        parsed_structure = (
            version.content_snapshot if version and version.content_snapshot else resume.parsed_structure
        )
        active_version_id = version.id if version else None

        analyses = await self.analysis_repo.list_by_resume(resume_id, limit=20)
        if active_version_id:
            version_analyses = [
                analysis
                for analysis in analyses
                if analysis.resume_version_id == active_version_id
                and analysis.status.value == "completed"
            ]
            latest = version_analyses[0] if version_analyses else None
        else:
            latest = await self.analysis_repo.get_latest_by_resume(resume_id)

        latest_analysis = None
        staleness = await compute_resume_staleness(
            self.session,
            resume_id=resume_id,
            parsed_structure=parsed_structure,
            resume_version_id=active_version_id,
        )
        if latest and latest.status.value == "completed":
            linked = await self._get_linked_ai_result(latest.id)
            latest_analysis = ResumeAnalyzer(
                get_ai_service(), self.session
            )._build_response(latest, linked, cached=False)
            latest_analysis["stale"] = staleness["analysis_stale"]

        meta = (parsed_structure or {}).get("_meta", {})

        from app.services.match_service import MatchService

        latest_job_match = await MatchService(self.session).get_latest_match_for_resume(
            resume_id,
            resume_version_id=active_version_id,
        )
        if latest_job_match is not None:
            latest_job_match["stale"] = staleness["match_stale"]

        return {
            "id": resume.id,
            "user_id": resume.user_id,
            "title": resume.title,
            "original_filename": resume.original_filename,
            "mime_type": resume.mime_type,
            "is_active": resume.is_active,
            "created_at": resume.created_at,
            "updated_at": resume.updated_at,
            "sections_found": meta.get("sections_found", []),
            "sections_missing": meta.get("sections_missing", []),
            "active_version_id": active_version_id,
            "active_version_label": version.label if version else None,
            "analysis_stale": staleness["analysis_stale"],
            "match_stale": staleness["match_stale"],
            "reanalyze_recommended": staleness["analysis_stale"] or staleness["match_stale"],
            "latest_analysis": latest_analysis,
            "latest_job_match": latest_job_match,
        }

    async def _get_linked_ai_result(self, analysis_id: UUID) -> AIAnalysisResult | None:
        return await AIAnalysisResultRepository(self.session).get_by_resume_analysis_id(
            analysis_id
        )

    async def list_dashboard_resumes(
        self,
        user_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict]:
        """List resumes for the authenticated user with latest analysis summary."""
        resumes = await self.resume_repo.list_by_user(user_id, skip=skip, limit=limit)
        latest_by_resume = await self.analysis_repo.get_latest_completed_for_resumes(
            [resume.id for resume in resumes]
        )
        items: list[dict] = []
        for resume in resumes:
            latest = latest_by_resume.get(resume.id)
            has_analysis = latest is not None
            items.append(
                {
                    "id": resume.id,
                    "title": resume.title,
                    "original_filename": resume.original_filename,
                    "created_at": resume.created_at,
                    "updated_at": resume.updated_at,
                    "overall_score": latest.overall_score if has_analysis else None,
                    "analyzed_at": latest.analyzed_at if has_analysis else None,
                    "has_analysis": has_analysis,
                }
            )
        return items

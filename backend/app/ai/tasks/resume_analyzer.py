"""Resume health score and explainability via AIService."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.database import MongoSession

from app.ai.client import AIService
from app.ai.prompts.loader import load_prompt
from app.ai.schemas.analysis_output import ResumeAnalysisOutput
from app.ai.utils import hash_resume_content
from app.core.exceptions import AppError
from app.models.enums import AIResultType, AIServiceName, AnalysisStatus
from app.repositories import (
    AIAnalysisResultRepository,
    ResumeAnalysisRepository,
    ResumeRepository,
    ResumeVersionRepository,
)
from app.utils.version_content import get_version_content, resolve_version

logger = logging.getLogger(__name__)

PROMPT_FILE = "resume_analyze_v1.yaml"
PROMPT_VERSION = "resume_analyze_v1"


class ResumeAnalyzer:
    """Analyzes a resume and produces health scores with explainability."""

    def __init__(self, ai_service: AIService, session: MongoSession) -> None:
        self.ai_service = ai_service
        self.session = session
        self.resume_repo = ResumeRepository(session)
        self.version_repo = ResumeVersionRepository(session)
        self.analysis_repo = ResumeAnalysisRepository(session)
        self.ai_result_repo = AIAnalysisResultRepository(session)

    async def analyze(
        self,
        resume_id: UUID,
        *,
        resume_version_id: UUID | None = None,
    ) -> dict[str, Any]:
        resume = await self.resume_repo.get_by_id(resume_id)
        if resume is None:
            raise AppError("Resume not found.", code="resume_not_found", status_code=404)

        version = await resolve_version(
            self.version_repo,
            resume_id,
            version_id=resume_version_id,
            required=False,
        )
        if version:
            parsed_structure = get_version_content(version)
            raw_text = version.raw_text or resume.raw_text or ""
        else:
            if not resume.parsed_structure:
                raise AppError(
                    "Resume has not been parsed yet. Upload and parse first.",
                    code="resume_not_parsed",
                    status_code=422,
                )
            parsed_structure = resume.parsed_structure
            raw_text = resume.raw_text or ""

        content_hash = hash_resume_content(parsed_structure)

        if resume_version_id:
            analyses = await self.analysis_repo.list_by_resume(resume_id, limit=20)
            latest = next(
                (
                    analysis
                    for analysis in analyses
                    if analysis.resume_version_id == resume_version_id
                    and analysis.status == AnalysisStatus.COMPLETED
                ),
                None,
            )
        else:
            latest = await self.analysis_repo.get_latest_by_resume(resume_id)

        if latest and latest.status == AnalysisStatus.COMPLETED:
            linked = await self._get_linked_ai_result(latest.id)
            if linked and linked.input_hash == content_hash:
                return self._build_response(latest, linked, cached=True)

        cached_ai = await self.ai_result_repo.get_by_input_hash_and_service(
            content_hash,
            AIServiceName.RESUME_ANALYZER,
        )
        if cached_ai:
            analysis = await self._persist_analysis_from_cache(
                resume_id=resume_id,
                resume_version_id=resume_version_id or (version.id if version else None),
                cached_ai=cached_ai,
            )
            return self._build_response(analysis, cached_ai, cached=True)

        return await self._run_fresh_analysis(
            resume_id=resume_id,
            resume_version_id=resume_version_id or (version.id if version else None),
            content_hash=content_hash,
            parsed_structure=parsed_structure,
            raw_text=raw_text,
        )

    async def _run_fresh_analysis(
        self,
        *,
        resume_id: UUID,
        resume_version_id: UUID | None,
        content_hash: str,
        parsed_structure: dict[str, Any],
        raw_text: str,
    ) -> dict[str, Any]:
        pending = await self.analysis_repo.create(
            resume_id=resume_id,
            resume_version_id=resume_version_id,
            status=AnalysisStatus.PENDING,
        )

        try:
            output, completion = await self._call_ai(parsed_structure, raw_text)
            analysis = await self._persist_completed_analysis(
                analysis=pending,
                output=output,
                content_hash=content_hash,
                resume_id=resume_id,
                resume_version_id=resume_version_id,
                model_used=completion.model_used,
                token_usage=completion.token_usage,
            )
            ai_result = await self.ai_result_repo.get_by_input_hash_and_service(
                content_hash,
                AIServiceName.RESUME_ANALYZER,
            )
            return self._build_response(analysis, ai_result, cached=False)
        except Exception:
            await self.analysis_repo.update(pending, status=AnalysisStatus.FAILED)
            raise

    async def _call_ai(
        self,
        parsed_structure: dict[str, Any],
        raw_text: str,
    ) -> tuple[ResumeAnalysisOutput, Any]:
        prompt_data = load_prompt(PROMPT_FILE)
        meta = parsed_structure.get("_meta", {})
        sections_found = meta.get("sections_found", [])
        sections_missing = meta.get("sections_missing", [])

        user_prompt = prompt_data["user_template"].format(
            resume_json=json.dumps(parsed_structure, indent=2, default=str),
            raw_text=raw_text[:8000],
            sections_found=sections_found,
            sections_missing=sections_missing,
        )

        return await self.ai_service.complete_structured(
            prompt=user_prompt,
            system_prompt=prompt_data["system"],
            output_schema=ResumeAnalysisOutput,
            prompt_version=PROMPT_VERSION,
        )

    async def _persist_completed_analysis(
        self,
        *,
        analysis: Any,
        output: ResumeAnalysisOutput,
        content_hash: str,
        resume_id: UUID,
        resume_version_id: UUID | None,
        model_used: str,
        token_usage: dict[str, Any] | None,
    ) -> Any:
        issues = [issue.model_dump() for issue in output.issues]
        dimensions = [dim.model_dump() for dim in output.dimensions]

        await self.analysis_repo.update(
            analysis,
            overall_score=output.overall_score,
            category_scores=output.category_scores,
            issues=issues,
            status=AnalysisStatus.COMPLETED,
            analyzed_at=datetime.now(UTC),
        )

        payload = {
            "overall_score": output.overall_score,
            "summary": output.summary,
            "dimensions": dimensions,
            "category_scores": output.category_scores,
            "issues": issues,
        }

        await self.ai_result_repo.create(
            service_name=AIServiceName.RESUME_ANALYZER,
            input_hash=content_hash,
            result_type=AIResultType.FULL_REPORT,
            payload=payload,
            model_used=model_used,
            prompt_version=PROMPT_VERSION,
            token_usage=token_usage,
            resume_id=resume_id,
            resume_version_id=resume_version_id,
            resume_analysis_id=analysis.id,
        )

        return analysis

    async def _persist_analysis_from_cache(
        self,
        *,
        resume_id: UUID,
        resume_version_id: UUID | None,
        cached_ai: Any,
    ) -> Any:
        payload = cached_ai.payload
        analysis = await self.analysis_repo.create(
            resume_id=resume_id,
            resume_version_id=resume_version_id,
            overall_score=self._extract_overall_from_payload(payload),
            category_scores=payload.get("category_scores"),
            issues=payload.get("issues"),
            status=AnalysisStatus.COMPLETED,
            analyzed_at=datetime.now(UTC),
        )

        await self.ai_result_repo.create(
            service_name=AIServiceName.RESUME_ANALYZER,
            input_hash=cached_ai.input_hash,
            result_type=AIResultType.FULL_REPORT,
            payload=payload,
            model_used=cached_ai.model_used,
            prompt_version=cached_ai.prompt_version,
            token_usage=None,
            resume_id=resume_id,
            resume_version_id=resume_version_id,
            resume_analysis_id=analysis.id,
        )

        return analysis

    async def _get_linked_ai_result(self, analysis_id: UUID) -> Any | None:
        return await AIAnalysisResultRepository(self.session).get_by_resume_analysis_id(
            analysis_id
        )

    def _extract_overall_from_payload(self, payload: dict[str, Any]) -> int | None:
        overall = payload.get("overall_score")
        if isinstance(overall, int):
            return overall
        dimensions = payload.get("dimensions", [])
        if not dimensions:
            return None
        scores = [d.get("score", 0) for d in dimensions if isinstance(d, dict)]
        return round(sum(scores) / len(scores)) if scores else None

    def _build_response(
        self,
        analysis: Any,
        ai_result: Any | None,
        *,
        cached: bool,
    ) -> dict[str, Any]:
        payload = ai_result.payload if ai_result else {}
        return {
            "analysis_id": analysis.id,
            "resume_id": analysis.resume_id,
            "resume_version_id": analysis.resume_version_id,
            "cached": cached,
            "overall_score": analysis.overall_score,
            "category_scores": analysis.category_scores or {},
            "summary": payload.get("summary", ""),
            "dimensions": payload.get("dimensions", []),
            "issues": analysis.issues or [],
            "status": analysis.status.value,
            "analyzed_at": analysis.analyzed_at,
            "prompt_version": ai_result.prompt_version if ai_result else PROMPT_VERSION,
        }

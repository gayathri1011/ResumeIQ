"""Orchestrates resume optimization workflows."""

from __future__ import annotations

from uuid import UUID

from app.core.database import MongoSession

from app.ai.client import get_ai_service
from app.ai.tasks.resume_optimizer import ResumeOptimizer
from app.core.exceptions import AppError
from app.models.enums import ResumeVersionSource, ResumeVersionStatus
from app.repositories import (
    AIAnalysisResultRepository,
    ResumeRepository,
    ResumeVersionRepository,
)
from app.utils.optimization_apply import (
    apply_optimization_decisions,
    build_bulk_decisions,
)
from app.utils.resume_staleness import (
    compute_resume_staleness,
    invalidate_resume_content_meta,
)
from app.utils.ownership import require_owned_resume
from app.utils.version_content import resolve_version, sync_resume_from_version, sync_version_content
from app.utils.version_create import create_resume_version


class OptimizerService:
    """Orchestrates resume optimization as a reviewable draft proposal."""

    def __init__(self, session: MongoSession) -> None:
        self.session = session
        self.resume_repo = ResumeRepository(session)
        self.version_repo = ResumeVersionRepository(session)
        self.ai_result_repo = AIAnalysisResultRepository(session)

    async def optimize_resume(
        self,
        resume_id: UUID,
        *,
        user_id: UUID,
        target_role: str,
        job_id: UUID | None = None,
        resume_version_id: UUID | None = None,
    ) -> dict:
        resume = await require_owned_resume(self.resume_repo, resume_id, user_id)

        version = await resolve_version(
            self.version_repo,
            resume_id,
            version_id=resume_version_id,
            required=False,
        )
        if version:
            await sync_resume_from_version(self.resume_repo, resume, version)

        optimizer = ResumeOptimizer(get_ai_service(), self.session)
        result = await optimizer.optimize(
            resume_id,
            target_role=target_role,
            job_description_id=job_id,
            resume_version_id=version.id if version else resume_version_id,
        )

        parent_version = version
        if parent_version is None:
            versions = await self.version_repo.list_by_resume(resume_id, limit=1)
            parent_version = versions[0] if versions else None
        label = f"Optimized for {target_role.strip()}"
        if job_id:
            label = f"{label} (JD-grounded)"

        draft_version = await create_resume_version(
            self.session,
            resume_id=resume_id,
            label=label,
            content_snapshot=result["optimized_content"],
            raw_text=resume.raw_text,
            source=ResumeVersionSource.OPTIMIZATION,
            status=ResumeVersionStatus.DRAFT,
            parent_version_id=parent_version.id if parent_version else None,
        )

        result["draft_version_id"] = draft_version.id
        result["draft_version_number"] = draft_version.version_number
        result["status"] = "draft"
        result["review_status"] = "pending"
        result["message"] = (
            "Optimization saved as a draft proposal. Review before applying to your live resume."
        )
        return result

    async def get_latest_optimization(
        self,
        resume_id: UUID,
        *,
        user_id: UUID,
        resume_version_id: UUID | None = None,
    ) -> dict | None:
        resume = await require_owned_resume(self.resume_repo, resume_id, user_id)

        ai_result = await self.ai_result_repo.get_latest_optimization_for_resume(resume_id)
        if ai_result is None:
            return None

        payload = ai_result.payload or {}
        if resume_version_id and payload.get("resume_version_id"):
            if str(payload.get("resume_version_id")) != str(resume_version_id):
                return None

        draft_versions = await self.version_repo.list_by_resume(resume_id, limit=10)
        draft_version = next(
            (
                version
                for version in draft_versions
                if version.source == ResumeVersionSource.OPTIMIZATION
                and version.status == ResumeVersionStatus.DRAFT
            ),
            None,
        )

        return {
            "optimization_id": ai_result.id,
            "resume_id": resume_id,
            "draft_version_id": draft_version.id if draft_version else None,
            "draft_version_number": draft_version.version_number if draft_version else None,
            "target_role": payload.get("target_role", ""),
            "job_description_id": payload.get("job_description_id"),
            "job_match_id": payload.get("job_match_id"),
            "optimization_mode": payload.get("optimization_mode", "target_role_only"),
            "status": "draft" if draft_version else payload.get("review_status", "reviewed"),
            "review_status": payload.get("review_status", "pending"),
            "message": "Review proposed optimization changes before applying to your live resume.",
            "original_content": payload.get("original_content") or resume.parsed_structure,
            "optimized_content": payload.get("optimized_content") or {},
            "changes": payload.get("changes") or [],
            "prompt_version": ai_result.prompt_version or payload.get("prompt_version"),
            "model_used": ai_result.model_used,
            "cached": False,
            "applied_change_ids": payload.get("applied_change_ids") or [],
        }

    async def apply_optimization(
        self,
        resume_id: UUID,
        optimization_id: UUID,
        *,
        user_id: UUID,
        decisions: list[dict[str, str]] | None = None,
        bulk_action: str | None = None,
        resume_version_id: UUID | None = None,
    ) -> dict:
        resume = await require_owned_resume(self.resume_repo, resume_id, user_id)

        ai_result = await self.ai_result_repo.get_by_id(optimization_id)
        if ai_result is None or ai_result.resume_id != resume_id:
            raise AppError("Optimization not found.", code="optimization_not_found", status_code=404)

        payload = dict(ai_result.payload or {})
        changes = payload.get("changes") or []
        if not changes:
            raise AppError(
                "This optimization has no changes to apply.",
                code="optimization_no_changes",
                status_code=422,
            )

        if bulk_action == "accept_all":
            decision_list = build_bulk_decisions(changes, action="accept")
        elif bulk_action == "reject_all":
            decision_list = build_bulk_decisions(changes, action="reject")
        elif decisions:
            decision_list = decisions
        else:
            raise AppError(
                "Provide decisions or a bulk_action.",
                code="decisions_required",
                status_code=422,
            )

        updated_content, accepted_ids = apply_optimization_decisions(
            current_content=resume.parsed_structure or payload.get("original_content") or {},
            original_content=payload.get("original_content") or {},
            optimized_content=payload.get("optimized_content") or {},
            changes=changes,
            decisions=decision_list,
        )

        message = "No changes were applied."
        staleness = await compute_resume_staleness(
            self.session,
            resume_id=resume_id,
            parsed_structure=resume.parsed_structure,
            resume_version_id=resume_version_id,
        )

        if accepted_ids:
            updated_content = invalidate_resume_content_meta(updated_content)
            await self.resume_repo.update(resume, parsed_structure=updated_content)

            target_version = await resolve_version(
                self.version_repo,
                resume_id,
                version_id=resume_version_id,
                required=False,
            )
            if target_version:
                await sync_version_content(
                    self.version_repo,
                    target_version,
                    updated_content,
                )
            else:
                active_versions = await self.version_repo.list_by_resume(resume_id, limit=5)
                for version in active_versions:
                    if version.status == ResumeVersionStatus.ACTIVE:
                        await sync_version_content(
                            self.version_repo,
                            version,
                            updated_content,
                        )
                        break

            staleness = await compute_resume_staleness(
                self.session,
                resume_id=resume_id,
                parsed_structure=updated_content,
            )
            message = (
                f"Applied {len(accepted_ids)} accepted change(s) to your live resume. "
                "Re-run analysis and job matching to refresh scores."
            )

        payload["applied_change_ids"] = list(
            set((payload.get("applied_change_ids") or []) + accepted_ids)
        )
        payload["review_status"] = (
            "applied"
            if len(payload["applied_change_ids"]) >= len(changes)
            else "partially_applied"
            if payload["applied_change_ids"]
            else "pending"
        )
        await self.ai_result_repo.update(ai_result, payload=payload)

        draft_versions = await self.version_repo.list_by_resume(resume_id, limit=10)
        for version in draft_versions:
            if (
                version.source == ResumeVersionSource.OPTIMIZATION
                and version.status == ResumeVersionStatus.DRAFT
            ):
                await self.version_repo.update(version, status=ResumeVersionStatus.ARCHIVED)
                break

        return {
            "resume_id": resume_id,
            "optimization_id": optimization_id,
            "accepted_change_ids": accepted_ids,
            "rejected_change_ids": [
                change["change_id"]
                for change in changes
                if change.get("change_id") not in accepted_ids
            ],
            "updated_content": updated_content if accepted_ids else resume.parsed_structure,
            "message": message,
            "analysis_stale": staleness["analysis_stale"],
            "match_stale": staleness["match_stale"],
            "reanalyze_recommended": staleness["analysis_stale"] or staleness["match_stale"],
        }

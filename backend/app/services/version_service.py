"""Resume version CRUD and lifecycle operations."""

from __future__ import annotations

import asyncio
import copy
import tempfile
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from app.core.database import MongoSession

from app.core.exceptions import AppError
from app.core.upload_errors import (
    CorruptedFileError,
    EmptyResumeError,
    ExtractionFailedError,
    FileTooLargeError,
    InvalidFileTypeError,
)
from app.models.enums import ExperienceLevel, ResumeVersionSource, ResumeVersionStatus
from app.models.job import JobMatch
from app.parsers.registry import parse_resume_file
from app.repositories import (
    AIAnalysisResultRepository,
    JobDescriptionRepository,
    JobMatchRepository,
    RecommendationRepository,
    ResumeAnalysisRepository,
    ResumeRepository,
    ResumeVersionRepository,
)
from app.services.resume_service import ResumeService
from app.utils.ownership import require_owned_resume
from app.utils.version_create import create_resume_version
from app.utils.version_content import (
    get_version_content,
    resolve_version,
    sync_resume_from_version,
)
from app.utils.version_master import get_master_version
from app.utils.version_status import compute_version_status, compute_versions_status_batch


class VersionService:
    """Manages resume versions as first-class content units."""

    def __init__(self, session: MongoSession) -> None:
        self.session = session
        self.resume_repo = ResumeRepository(session)
        self.version_repo = ResumeVersionRepository(session)
        self.job_repo = JobDescriptionRepository(session)
        self.match_repo = JobMatchRepository(session)
        self.analysis_repo = ResumeAnalysisRepository(session)
        self.recommendation_repo = RecommendationRepository(session)
        self.ai_result_repo = AIAnalysisResultRepository(session)

    def _version_fields(self, version, status: dict, *, master_id: UUID | None = None) -> dict:
        is_master = version.is_master or (
            master_id is not None and version.id == master_id
        )
        return {
            "id": version.id,
            "resume_id": version.resume_id,
            "version_number": version.version_number,
            "label": version.label,
            "source": version.source,
            "status": version.status,
            "is_master": is_master,
            "target_role": version.target_role,
            "target_company": version.target_company,
            "experience_level": version.experience_level,
            "overall_score": version.overall_score or status.get("overall_score"),
            "ats_score": version.ats_score,
            "job_match_score": version.job_match_score,
            "role_relevance_score": version.role_relevance_score,
            "status_key": status["status_key"],
            "status_label": status["status_label"],
            "analysis_stale": status["analysis_stale"],
            "match_stale": status["match_stale"],
            "reanalyze_recommended": status["reanalyze_recommended"],
            "latest_match_score": status["latest_match_score"],
            "parent_version_id": version.parent_version_id,
            "created_at": version.created_at,
            "updated_at": version.updated_at,
        }

    async def list_versions(
        self,
        resume_id: UUID,
        *,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict]:
        await require_owned_resume(self.resume_repo, resume_id, user_id)

        versions = await self.version_repo.list_by_resume(resume_id, skip=skip, limit=limit)
        master_version = await get_master_version(self.version_repo, resume_id)
        if not master_version.is_master:
            await self.version_repo.update(master_version, is_master=True)
            master_version.is_master = True
        status_by_version = await compute_versions_status_batch(self.session, versions)
        master_id = master_version.id

        match_ids: list[UUID] = []
        for status in status_by_version.values():
            match_id = status.get("latest_match_id")
            if match_id:
                match_ids.append(match_id)

        matches_by_id = await self.match_repo.get_by_ids(match_ids)

        jobs_by_id = await self.job_repo.get_by_ids(
            [
                match.job_description_id
                for match in matches_by_id.values()
                if match.job_description_id
            ]
        )

        items: list[dict] = []
        for version in versions:
            status = status_by_version[version.id]
            job_title = None
            company = None
            if status["latest_match_id"]:
                match = matches_by_id.get(status["latest_match_id"])
                if match:
                    job = jobs_by_id.get(match.job_description_id)
                    if job:
                        parsed = job.parsed_requirements or {}
                        job_title = parsed.get("job_title") or job.title
                        company = job.company

            items.append(
                {
                    **self._version_fields(version, status, master_id=master_id),
                    "latest_match_job_title": job_title,
                    "latest_match_company": company,
                    "latest_match_id": status["latest_match_id"],
                }
            )
        return items

    async def get_version(self, resume_id: UUID, version_id: UUID, *, user_id: UUID) -> dict:
        await require_owned_resume(self.resume_repo, resume_id, user_id)
        version = await self.version_repo.get_by_resume_and_id(resume_id, version_id)
        if version is None:
            raise AppError("Resume version not found.", code="resume_version_not_found", status_code=404)

        status = await compute_version_status(self.session, version)
        master_version = await get_master_version(self.version_repo, resume_id)
        return {
            **self._version_fields(version, status, master_id=master_version.id),
            "content_snapshot": version.content_snapshot,
            "raw_text": version.raw_text,
            "job_description_text": version.job_description_text,
            "transformation_metadata": version.transformation_metadata,
            "ai_analysis_result_id": version.ai_analysis_result_id,
            "latest_match_job_title": None,
            "latest_match_company": None,
            "latest_match_id": status.get("latest_match_id"),
        }

    async def create_version(
        self,
        resume_id: UUID,
        *,
        user_id: UUID,
        label: str,
        duplicate_from_version_id: UUID | None = None,
        upload: UploadFile | None = None,
    ) -> dict:
        resume = await require_owned_resume(self.resume_repo, resume_id, user_id)

        parent_version_id = duplicate_from_version_id

        if upload is not None:
            resume_service = ResumeService(self.session)
            content = await upload.read()
            filename = upload.filename or "resume"
            resume_service._validate_upload(filename, upload.content_type, len(content))

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
                    upload.content_type,
                )
            except (
                CorruptedFileError,
                EmptyResumeError,
                ExtractionFailedError,
                InvalidFileTypeError,
            ):
                raise
            except Exception as exc:
                raise ExtractionFailedError() from exc
            finally:
                if tmp_path is not None:
                    tmp_path.unlink(missing_ok=True)

            parsed_dict = parsed_doc.structured.to_storage_dict()
            version = await create_resume_version(
                self.session,
                resume_id=resume_id,
                label=label.strip(),
                content_snapshot=parsed_dict,
                raw_text=parsed_doc.raw_text,
                source=ResumeVersionSource.UPLOAD,
                status=ResumeVersionStatus.ACTIVE,
                parent_version_id=parent_version_id,
            )
        else:
            if duplicate_from_version_id is None:
                raise AppError(
                    "Provide a file upload or duplicate_from_version_id.",
                    code="version_create_invalid",
                    status_code=422,
                )

            source_version = await self.version_repo.get_by_resume_and_id(
                resume_id,
                duplicate_from_version_id,
            )
            if source_version is None:
                raise AppError(
                    "Source version not found.",
                    code="resume_version_not_found",
                    status_code=404,
                )

            version = await create_resume_version(
                self.session,
                resume_id=resume_id,
                label=label.strip(),
                content_snapshot=copy.deepcopy(source_version.content_snapshot),
                raw_text=source_version.raw_text,
                source=ResumeVersionSource.MANUAL,
                status=ResumeVersionStatus.ACTIVE,
                parent_version_id=source_version.id,
            )

        if upload is not None or version.is_master:
            await sync_resume_from_version(self.resume_repo, resume, version)
        return await self.get_version(resume_id, version.id, user_id=user_id)

    async def rename_version(
        self,
        resume_id: UUID,
        version_id: UUID,
        *,
        user_id: UUID,
        label: str,
    ) -> dict:
        await require_owned_resume(self.resume_repo, resume_id, user_id)
        version = await self.version_repo.get_by_resume_and_id(resume_id, version_id)
        if version is None:
            raise AppError("Resume version not found.", code="resume_version_not_found", status_code=404)

        await self.version_repo.update(version, label=label.strip())
        return await self.get_version(resume_id, version_id, user_id=user_id)

    async def delete_version(self, resume_id: UUID, version_id: UUID, *, user_id: UUID) -> dict:
        await require_owned_resume(self.resume_repo, resume_id, user_id)
        version = await self.version_repo.get_by_resume_and_id(resume_id, version_id)
        if version is None:
            raise AppError("Resume version not found.", code="resume_version_not_found", status_code=404)

        if version.is_master:
            raise AppError(
                "Cannot delete the master resume version.",
                code="version_delete_master",
                status_code=422,
            )

        count = await self.version_repo.count_by_resume(resume_id)
        if count <= 1:
            raise AppError(
                "Cannot delete the only remaining version for this resume.",
                code="version_delete_last",
                status_code=422,
            )

        await self._cleanup_version_records(version_id)
        await self.version_repo.delete(version)

        remaining = await self.version_repo.list_by_resume(resume_id, limit=1)
        if remaining:
            resume = await self.resume_repo.get_by_id(resume_id)
            if resume:
                await sync_resume_from_version(self.resume_repo, resume, remaining[0])

        return {"message": "Version deleted.", "resume_id": resume_id, "version_id": version_id}

    async def _cleanup_version_records(self, version_id: UUID) -> None:
        match_ids = await self.match_repo.delete_by_resume_version_id(version_id)
        await self.recommendation_repo.delete_by_job_match_ids(match_ids)
        await self.ai_result_repo.delete_by_resume_version_id(version_id)
        await self.analysis_repo.delete_by_resume_version_id(version_id)

    async def analyze_version(self, resume_id: UUID, version_id: UUID, *, user_id: UUID) -> dict:
        await require_owned_resume(self.resume_repo, resume_id, user_id)
        version = await resolve_version(self.version_repo, resume_id, version_id=version_id)
        resume = await self.resume_repo.get_by_id(resume_id)
        if resume is None:
            raise AppError("Resume not found.", code="resume_not_found", status_code=404)

        if version.is_master:
            await sync_resume_from_version(self.resume_repo, resume, version)

        from app.services.analysis_service import AnalysisService

        return await AnalysisService(self.session).analyze_resume(
            resume_id,
            user_id=user_id,
            resume_version_id=version.id,
        )

    async def optimize_version(
        self,
        resume_id: UUID,
        version_id: UUID,
        *,
        user_id: UUID,
        target_role: str,
        job_id: UUID | None = None,
    ) -> dict:
        await require_owned_resume(self.resume_repo, resume_id, user_id)
        version = await resolve_version(self.version_repo, resume_id, version_id=version_id)
        resume = await self.resume_repo.get_by_id(resume_id)
        if resume is None:
            raise AppError("Resume not found.", code="resume_not_found", status_code=404)

        await sync_resume_from_version(self.resume_repo, resume, version)

        from app.services.optimizer_service import OptimizerService

        return await OptimizerService(self.session).optimize_resume(
            resume_id,
            user_id=user_id,
            target_role=target_role,
            job_id=job_id,
            resume_version_id=version.id,
        )

    async def generate_role_version(
        self,
        resume_id: UUID,
        *,
        user_id: UUID,
        target_role: str,
        target_company: str | None = None,
        job_description: str | None = None,
        experience_level: ExperienceLevel | None = None,
        master_version_id: UUID | None = None,
    ) -> dict:
        """Generate a complete role-specific resume version from the master resume."""
        await require_owned_resume(self.resume_repo, resume_id, user_id)

        if master_version_id:
            master_version = await self.version_repo.get_by_resume_and_id(resume_id, master_version_id)
            if master_version is None:
                raise AppError("Master version not found.", code="resume_version_not_found", status_code=404)
        else:
            master_version = await get_master_version(self.version_repo, resume_id)

        from app.ai.client import get_ai_service
        from app.ai.tasks.role_version_transformer import RoleVersionTransformer

        transformer = RoleVersionTransformer(get_ai_service(), self.session)
        result = await transformer.transform(
            resume_id,
            master_version_id=master_version.id,
            target_role=target_role,
            target_company=target_company,
            job_description_text=job_description,
            experience_level=experience_level,
        )

        label = target_role.strip()
        version = await create_resume_version(
            self.session,
            resume_id=resume_id,
            label=label,
            content_snapshot=result["optimized_content"],
            raw_text=master_version.raw_text,
            source=ResumeVersionSource.ROLE_TRANSFORMATION,
            status=ResumeVersionStatus.ACTIVE,
            parent_version_id=master_version.id,
            target_role=target_role.strip(),
            target_company=target_company,
            job_description_text=job_description,
            experience_level=experience_level,
            ats_score=result.get("ats_score"),
            job_match_score=result.get("job_match_score"),
            role_relevance_score=result.get("role_relevance_score"),
            transformation_metadata={
                "insights": result.get("insights"),
                "job_match_details": result.get("job_match_details"),
                "changes": result.get("changes"),
                "original_content": result.get("original_content"),
            },
            ai_analysis_result_id=result["transformation_id"],
        )

        return {
            "version": await self.get_version(resume_id, version.id, user_id=user_id),
            "transformation_id": result["transformation_id"],
            "target_role": target_role.strip(),
            "message": f"Created role-specific version for {target_role.strip()}.",
        }

    async def get_version_transformation(
        self,
        resume_id: UUID,
        version_id: UUID,
        *,
        user_id: UUID,
    ) -> dict:
        await require_owned_resume(self.resume_repo, resume_id, user_id)
        version = await self.version_repo.get_by_resume_and_id(resume_id, version_id)
        if version is None:
            raise AppError("Resume version not found.", code="resume_version_not_found", status_code=404)

        metadata = version.transformation_metadata or {}
        if version.ai_analysis_result_id:
            ai_result = await self.ai_result_repo.get_by_id(version.ai_analysis_result_id)
            if ai_result and ai_result.payload:
                payload = ai_result.payload
                return {
                    "transformation_id": ai_result.id,
                    "target_role": version.target_role or payload.get("target_role"),
                    "target_company": version.target_company or payload.get("target_company"),
                    "experience_level": version.experience_level,
                    "original_content": payload.get("original_content") or metadata.get("original_content"),
                    "optimized_content": version.content_snapshot or payload.get("optimized_content"),
                    "changes": payload.get("changes") or metadata.get("changes") or [],
                    "insights": payload.get("insights") or metadata.get("insights") or {},
                    "role_relevance_score": version.role_relevance_score or payload.get("role_relevance_score"),
                    "ats_score": version.ats_score or payload.get("ats_score"),
                    "job_match_score": version.job_match_score or payload.get("job_match_score"),
                    "job_match_details": payload.get("job_match_details") or metadata.get("job_match_details") or {},
                }

        return {
            "transformation_id": version.ai_analysis_result_id,
            "target_role": version.target_role,
            "target_company": version.target_company,
            "experience_level": version.experience_level,
            "original_content": metadata.get("original_content"),
            "optimized_content": version.content_snapshot,
            "changes": metadata.get("changes") or [],
            "insights": metadata.get("insights") or {},
            "role_relevance_score": version.role_relevance_score,
            "ats_score": version.ats_score,
            "job_match_score": version.job_match_score,
            "job_match_details": metadata.get("job_match_details") or {},
        }

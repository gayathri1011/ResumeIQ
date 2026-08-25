"""Helpers for identifying and resolving the master resume version."""

from __future__ import annotations

from uuid import UUID

from app.core.exceptions import AppError
from app.models.enums import ResumeVersionSource
from app.models.resume import ResumeVersion
from app.repositories import ResumeVersionRepository


async def get_master_version(
    version_repo: ResumeVersionRepository,
    resume_id: UUID,
) -> ResumeVersion:
    versions = await version_repo.list_by_resume(resume_id, limit=50)
    if not versions:
        raise AppError(
            "No resume versions found.",
            code="resume_version_not_found",
            status_code=404,
        )

    master = next((version for version in versions if version.is_master), None)
    if master is None:
        master = next(
            (version for version in versions if version.source == ResumeVersionSource.UPLOAD),
            None,
        )
    if master is None:
        master = min(versions, key=lambda version: version.version_number)
    return master

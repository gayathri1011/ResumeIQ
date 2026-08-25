"""Helpers for resolving and syncing resume version content."""

from __future__ import annotations

import copy
from typing import Any
from uuid import UUID

from app.core.exceptions import AppError
from app.models.enums import ResumeVersionStatus
from app.models.resume import Resume, ResumeVersion
from app.repositories import ResumeRepository, ResumeVersionRepository


async def resolve_version(
    version_repo: ResumeVersionRepository,
    resume_id: UUID,
    *,
    version_id: UUID | None = None,
    required: bool = True,
) -> ResumeVersion | None:
    if version_id is not None:
        version = await version_repo.get_by_id(version_id)
        if version is None or version.resume_id != resume_id:
            raise AppError(
                "Resume version not found.",
                code="resume_version_not_found",
                status_code=404,
            )
        return version

    versions = await version_repo.list_by_resume(resume_id, limit=50)
    if not versions:
        if required:
            raise AppError(
                "No resume versions found.",
                code="resume_version_not_found",
                status_code=404,
            )
        return None

    active = next(
        (version for version in versions if version.status == ResumeVersionStatus.ACTIVE),
        None,
    )
    return active or versions[0]


def get_version_content(version: ResumeVersion) -> dict[str, Any]:
    if not version.content_snapshot:
        raise AppError(
            "Version has no parsed content.",
            code="resume_not_parsed",
            status_code=422,
        )
    return copy.deepcopy(version.content_snapshot)


async def sync_resume_from_version(
    resume_repo: ResumeRepository,
    resume: Resume,
    version: ResumeVersion,
) -> Resume:
    if not version.content_snapshot:
        return resume
    return await resume_repo.update(
        resume,
        parsed_structure=copy.deepcopy(version.content_snapshot),
        raw_text=version.raw_text or resume.raw_text,
    )


async def sync_version_content(
    version_repo: ResumeVersionRepository,
    version: ResumeVersion,
    content: dict[str, Any],
    *,
    raw_text: str | None = None,
) -> ResumeVersion:
    kwargs: dict[str, Any] = {"content_snapshot": copy.deepcopy(content)}
    if raw_text is not None:
        kwargs["raw_text"] = raw_text
    return await version_repo.update(version, **kwargs)

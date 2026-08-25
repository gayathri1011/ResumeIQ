from __future__ import annotations

import uuid
from typing import Any

from pymongo import ASCENDING, DESCENDING, IndexModel

from app.core.database import MongoDocument
from app.models.enums import ExperienceLevel, ResumeVersionSource, ResumeVersionStatus


class Resume(MongoDocument):
    user_id: uuid.UUID | None = None
    title: str
    original_filename: str | None = None
    file_path: str | None = None
    mime_type: str | None = None
    raw_text: str | None = None
    parsed_structure: dict[str, Any] | None = None
    content_embedding: list[float] | None = None
    is_active: bool = True

    class Settings:
        name = "resumes"
        indexes = [
            IndexModel([("user_id", ASCENDING), ("is_active", ASCENDING)]),
            IndexModel([("user_id", ASCENDING), ("updated_at", DESCENDING)]),
        ]

    def __repr__(self) -> str:
        return f"<Resume id={self.id} title={self.title!r}>"


class ResumeVersion(MongoDocument):
    resume_id: uuid.UUID
    version_number: int
    label: str | None = None
    content_snapshot: dict[str, Any] | None = None
    raw_text: str | None = None
    content_embedding: list[float] | None = None
    source: ResumeVersionSource = ResumeVersionSource.UPLOAD
    status: ResumeVersionStatus = ResumeVersionStatus.ACTIVE
    overall_score: int | None = None
    ats_score: int | None = None
    job_match_score: int | None = None
    role_relevance_score: int | None = None
    target_role: str | None = None
    target_company: str | None = None
    job_description_text: str | None = None
    experience_level: ExperienceLevel | None = None
    transformation_metadata: dict[str, Any] | None = None
    ai_analysis_result_id: uuid.UUID | None = None
    is_master: bool = False
    parent_version_id: uuid.UUID | None = None

    class Settings:
        name = "resume_versions"
        indexes = [
            IndexModel(
                [("resume_id", ASCENDING), ("version_number", ASCENDING)],
                unique=True,
            ),
            IndexModel([("resume_id", ASCENDING), ("version_number", DESCENDING)]),
        ]

    def __repr__(self) -> str:
        return f"<ResumeVersion id={self.id} resume_id={self.resume_id} v={self.version_number}>"

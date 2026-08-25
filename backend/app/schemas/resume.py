import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.models.enums import ResumeVersionSource, ResumeVersionStatus
from app.schemas.common import BaseSchema, TimestampSchema


class ResumeCreate(BaseSchema):
    user_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    original_filename: str | None = Field(default=None, max_length=512)
    file_path: str | None = Field(default=None, max_length=1024)
    mime_type: str | None = Field(default=None, max_length=128)
    raw_text: str | None = None
    parsed_structure: dict[str, Any] | None = None
    is_active: bool = True


class ResumeUpdate(BaseSchema):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    original_filename: str | None = Field(default=None, max_length=512)
    file_path: str | None = Field(default=None, max_length=1024)
    mime_type: str | None = Field(default=None, max_length=128)
    raw_text: str | None = None
    parsed_structure: dict[str, Any] | None = None
    is_active: bool | None = None


class ResumeRead(TimestampSchema):
    id: uuid.UUID
    user_id: uuid.UUID | None
    title: str
    original_filename: str | None
    file_path: str | None
    mime_type: str | None
    raw_text: str | None
    parsed_structure: dict[str, Any] | None
    is_active: bool


class ResumeUploadResponse(BaseSchema):
    id: uuid.UUID
    title: str
    original_filename: str | None
    file_size_bytes: int
    mime_type: str | None
    sections_found: list[str]
    sections_missing: list[str]
    created_at: datetime


class ResumeListItem(BaseSchema):
    id: uuid.UUID
    title: str
    original_filename: str | None
    created_at: datetime
    updated_at: datetime
    overall_score: int | None = None
    analyzed_at: datetime | None = None
    has_analysis: bool = False


class ResumeVersionCreate(BaseSchema):
    resume_id: uuid.UUID
    version_number: int = Field(ge=1)
    label: str | None = Field(default=None, max_length=255)
    content_snapshot: dict[str, Any] | None = None
    raw_text: str | None = None
    source: ResumeVersionSource = ResumeVersionSource.UPLOAD
    status: ResumeVersionStatus = ResumeVersionStatus.ACTIVE
    overall_score: int | None = Field(default=None, ge=0, le=100)
    parent_version_id: uuid.UUID | None = None


class ResumeVersionUpdate(BaseSchema):
    label: str | None = Field(default=None, max_length=255)
    content_snapshot: dict[str, Any] | None = None
    raw_text: str | None = None
    status: ResumeVersionStatus | None = None
    overall_score: int | None = Field(default=None, ge=0, le=100)


class ResumeVersionRead(TimestampSchema):
    id: uuid.UUID
    resume_id: uuid.UUID
    version_number: int
    label: str | None
    content_snapshot: dict[str, Any] | None
    raw_text: str | None
    source: ResumeVersionSource
    status: ResumeVersionStatus
    overall_score: int | None
    parent_version_id: uuid.UUID | None

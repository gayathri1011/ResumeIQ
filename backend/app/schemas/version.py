"""Extended schemas for role-specific resume version management."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.models.enums import ExperienceLevel, ResumeVersionSource, ResumeVersionStatus
from app.schemas.common import BaseSchema, TimestampSchema


class CreateVersionRequest(BaseSchema):
    label: str = Field(min_length=1, max_length=255)
    duplicate_from_version_id: uuid.UUID | None = None


class GenerateRoleVersionRequest(BaseSchema):
    target_role: str = Field(min_length=1, max_length=255)
    target_company: str | None = Field(default=None, max_length=255)
    job_description: str | None = Field(default=None, max_length=15000)
    experience_level: ExperienceLevel | None = None
    master_version_id: uuid.UUID | None = None


class UpdateVersionRequest(BaseSchema):
    label: str = Field(min_length=1, max_length=255)


class VersionListItem(BaseSchema):
    id: uuid.UUID
    resume_id: uuid.UUID
    version_number: int
    label: str | None
    source: ResumeVersionSource
    status: ResumeVersionStatus
    is_master: bool = False
    target_role: str | None = None
    target_company: str | None = None
    experience_level: ExperienceLevel | None = None
    overall_score: int | None = None
    ats_score: int | None = None
    job_match_score: int | None = None
    role_relevance_score: int | None = None
    status_key: str
    status_label: str
    analysis_stale: bool = False
    match_stale: bool = False
    reanalyze_recommended: bool = False
    latest_match_score: int | None = None
    latest_match_job_title: str | None = None
    latest_match_company: str | None = None
    latest_match_id: uuid.UUID | None = None
    parent_version_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class TransformationInsightSection(BaseSchema):
    section: str
    headline: str
    explanation: str


class TransformationInsights(BaseSchema):
    summary: str = ""
    sections: list[TransformationInsightSection] = Field(default_factory=list)
    top_strengths: list[str] = Field(default_factory=list)
    recommended_improvements: list[str] = Field(default_factory=list)


class JobMatchDetails(BaseSchema):
    match_score: int | None = None
    matched_requirements: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    explanation: str = ""


class VersionTransformationChange(BaseSchema):
    change_id: str
    section: str
    field_path: str | None = None
    before: str = ""
    after: str = ""
    why: str


class VersionDetailResponse(VersionListItem):
    content_snapshot: dict[str, Any] | None = None
    raw_text: str | None = None
    job_description_text: str | None = None
    transformation_metadata: dict[str, Any] | None = None
    ai_analysis_result_id: uuid.UUID | None = None


class GenerateRoleVersionResponse(BaseSchema):
    version: VersionDetailResponse
    transformation_id: uuid.UUID
    target_role: str
    message: str


class VersionTransformationResponse(BaseSchema):
    transformation_id: uuid.UUID | None = None
    target_role: str | None = None
    target_company: str | None = None
    experience_level: ExperienceLevel | None = None
    original_content: dict[str, Any] | None = None
    optimized_content: dict[str, Any] | None = None
    changes: list[VersionTransformationChange] = Field(default_factory=list)
    insights: TransformationInsights = Field(default_factory=TransformationInsights)
    role_relevance_score: int | None = None
    ats_score: int | None = None
    job_match_score: int | None = None
    job_match_details: JobMatchDetails = Field(default_factory=JobMatchDetails)


class VersionOptimizeRequest(BaseSchema):
    target_role: str = Field(min_length=1, max_length=255)
    job_id: uuid.UUID | None = None

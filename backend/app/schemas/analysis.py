import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.models.enums import AnalysisStatus
from app.schemas.common import BaseSchema, TimestampSchema

# Forward reference avoided — job match summary on resume detail
class LatestJobMatchSummary(BaseSchema):
    match_id: uuid.UUID
    job_description_id: uuid.UUID
    job_title: str | None = None
    company: str | None = None
    match_score: int
    semantic_score: float | None = None
    breakdown: dict[str, Any] | None = None
    summary: str = ""
    matched_at: datetime | None = None
    stale: bool = False


class DimensionScoreRead(BaseSchema):
    key: str
    score: int
    explanation: str
    disclaimer: str | None = None


class AnalysisIssueRead(BaseSchema):
    severity: str
    category: str
    title: str
    description: str
    suggested_fix: str | None = None
    grounded_in_resume: bool = True


class AnalyzeResumeResponse(BaseSchema):
    analysis_id: uuid.UUID
    resume_id: uuid.UUID
    resume_version_id: uuid.UUID | None = None
    cached: bool
    stale: bool = False
    overall_score: int | None
    category_scores: dict[str, int]
    summary: str
    dimensions: list[DimensionScoreRead]
    issues: list[AnalysisIssueRead]
    status: str
    analyzed_at: datetime | None
    prompt_version: str


class ResumeAnalysisCreate(BaseSchema):
    resume_id: uuid.UUID
    resume_version_id: uuid.UUID | None = None
    overall_score: int | None = Field(default=None, ge=0, le=100)
    category_scores: dict[str, Any] | None = None
    issues: list[Any] | None = None
    status: AnalysisStatus = AnalysisStatus.PENDING
    analyzed_at: datetime | None = None


class ResumeAnalysisUpdate(BaseSchema):
    overall_score: int | None = Field(default=None, ge=0, le=100)
    category_scores: dict[str, Any] | None = None
    issues: list[Any] | None = None
    status: AnalysisStatus | None = None
    analyzed_at: datetime | None = None


class ResumeAnalysisRead(TimestampSchema):
    id: uuid.UUID
    resume_id: uuid.UUID
    resume_version_id: uuid.UUID | None
    overall_score: int | None
    category_scores: dict[str, Any] | None
    issues: list[Any] | None
    status: AnalysisStatus
    analyzed_at: datetime | None


class ResumeDetailResponse(BaseSchema):
    id: uuid.UUID
    user_id: uuid.UUID | None
    title: str
    original_filename: str | None
    mime_type: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    sections_found: list[str]
    sections_missing: list[str]
    active_version_id: uuid.UUID | None = None
    active_version_label: str | None = None
    analysis_stale: bool = False
    match_stale: bool = False
    reanalyze_recommended: bool = False
    latest_analysis: AnalyzeResumeResponse | None = None
    latest_job_match: LatestJobMatchSummary | None = None

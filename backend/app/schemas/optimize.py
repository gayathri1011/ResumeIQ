"""Resume optimization API schemas."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import Field

from app.schemas.common import BaseSchema


class OptimizeResumeRequest(BaseSchema):
    target_role: str = Field(min_length=1, max_length=255)
    job_id: uuid.UUID | None = None
    resume_version_id: uuid.UUID | None = None


class OptimizationChangeItem(BaseSchema):
    change_id: str
    section: str
    field_path: str | None = None
    before: str = ""
    after: str = ""
    why: str


class OptimizeResumeResponse(BaseSchema):
    optimization_id: uuid.UUID
    resume_id: uuid.UUID
    draft_version_id: uuid.UUID | None = None
    draft_version_number: int | None = None
    target_role: str
    job_description_id: uuid.UUID | None = None
    job_match_id: uuid.UUID | None = None
    optimization_mode: str
    status: str
    review_status: str = "pending"
    message: str
    original_content: dict[str, Any]
    optimized_content: dict[str, Any]
    changes: list[OptimizationChangeItem]
    prompt_version: str
    model_used: str | None = None
    cached: bool = False
    applied_change_ids: list[str] = Field(default_factory=list)


class OptimizationDecisionItem(BaseSchema):
    change_id: str = Field(min_length=1)
    action: str = Field(pattern="^(accept|reject)$")


class ApplyOptimizationRequest(BaseSchema):
    optimization_id: uuid.UUID
    resume_version_id: uuid.UUID | None = None
    decisions: list[OptimizationDecisionItem] | None = None
    bulk_action: str | None = Field(default=None, pattern="^(accept_all|reject_all)$")


class ApplyOptimizationResponse(BaseSchema):
    resume_id: uuid.UUID
    optimization_id: uuid.UUID
    accepted_change_ids: list[str]
    rejected_change_ids: list[str]
    updated_content: dict[str, Any]
    message: str
    analysis_stale: bool
    match_stale: bool
    reanalyze_recommended: bool


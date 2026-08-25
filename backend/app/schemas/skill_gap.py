"""Skill gap API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.schemas.common import BaseSchema


class MissingSkillItem(BaseSchema):
    skill: str
    priority: Literal["high", "medium", "low"]
    source: str
    why_it_matters: str


class RoadmapStepRead(BaseSchema):
    skill: str
    rationale: str


class SkillGapResponse(BaseSchema):
    job_match_id: uuid.UUID
    job_description_id: uuid.UUID
    resume_id: uuid.UUID
    resume_version_id: uuid.UUID | None = None
    cached: bool
    target_role: str | None = None
    company: str | None = None
    skill_coverage_percent: float
    coverage_meta: dict[str, Any] = Field(default_factory=dict)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[MissingSkillItem] = Field(default_factory=list)
    learning_roadmap: list[RoadmapStepRead] = Field(default_factory=list)
    match_score: int
    analyzed_at: datetime | None = None
    prompt_version: str = "skill_gap_v1"

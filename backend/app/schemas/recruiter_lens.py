from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import BaseSchema


class RecruiterSnapshotRead(BaseSchema):
    target_role: str
    experience: str
    strongest_skills: list[str] = Field(default_factory=list)
    domain: str
    differentiator: str


class RecruiterScoreRead(BaseSchema):
    key: str
    label: str
    score: int = Field(ge=0, le=100)
    explanation: str


class RecruiterAttentionRead(BaseSchema):
    area: str
    visibility: int = Field(ge=0, le=100)
    rationale: str


class RecruiterEvidenceRead(BaseSchema):
    title: str
    evidence: str


class RecruiterRiskRead(BaseSchema):
    issue: str
    reason: str


class RecruiterImprovementRead(BaseSchema):
    action: str
    reason: str


class RecruiterLensResponse(BaseSchema):
    lens_id: uuid.UUID
    resume_id: uuid.UUID
    resume_version_id: uuid.UUID | None = None
    cached: bool
    recruiter_snapshot: RecruiterSnapshotRead
    first_impression: str
    clarity: str
    scores: list[RecruiterScoreRead] = Field(min_length=5, max_length=5)
    attention_map: list[RecruiterAttentionRead] = Field(min_length=1)
    visible_strengths: list[RecruiterEvidenceRead] = Field(default_factory=list)
    potentially_missed: list[RecruiterEvidenceRead] = Field(default_factory=list)
    risks: list[RecruiterRiskRead] = Field(default_factory=list)
    improvements: list[RecruiterImprovementRead] = Field(default_factory=list)
    current_positioning: str
    recommended_positioning: str
    limitations: list[str] = Field(default_factory=list)
    analyzed_at: datetime
    prompt_version: str

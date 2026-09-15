from __future__ import annotations

import uuid
from typing import Literal

from pydantic import Field

from app.schemas.common import BaseSchema


class TrajectoryFactorRead(BaseSchema):
    key: str
    label: str
    score: int = Field(ge=0, le=100)
    weight: int = Field(ge=0, le=100)
    explanation: str


class TrajectoryPathRead(BaseSchema):
    role: str
    timeframe: str
    readiness_score: int = Field(ge=0, le=100)
    summary: str
    matched_skills: list[str] = Field(default_factory=list)
    skill_gaps: list[str] = Field(default_factory=list)
    proof_gaps: list[str] = Field(default_factory=list)
    factors: list[TrajectoryFactorRead] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class CareerTrajectoryResponse(BaseSchema):
    trajectory_id: uuid.UUID
    resume_id: uuid.UUID
    resume_version_id: uuid.UUID | None = None
    cached: bool
    current_profile: str
    profile_summary: str
    paths: list[TrajectoryPathRead] = Field(min_length=1, max_length=5)
    limitations: list[str] = Field(default_factory=list)
    analyzed_at: str | None = None
    prompt_version: str

from __future__ import annotations

from pydantic import BaseModel, Field


class TrajectoryRoleOutput(BaseModel):
    role: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    required_skills: list[str] = Field(default_factory=list)
    experience_signals: list[str] = Field(default_factory=list)
    seniority_level: str = Field(min_length=1)
    role_fit_reason: str = Field(min_length=1)
    resume_evidence: list[str] = Field(default_factory=list)
    likely_skill_gaps: list[str] = Field(default_factory=list)
    likely_proof_gaps: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class CareerTrajectoryOutput(BaseModel):
    current_profile: str = Field(min_length=1)
    profile_summary: str = Field(min_length=1)
    paths: list[TrajectoryRoleOutput] = Field(min_length=1, max_length=5)
    limitations: list[str] = Field(default_factory=list)

from __future__ import annotations

from pydantic import BaseModel, Field


class RecruiterSnapshotOutput(BaseModel):
    target_role: str = Field(min_length=1)
    experience: str = Field(min_length=1)
    strongest_skills: list[str] = Field(default_factory=list)
    domain: str = Field(min_length=1)
    differentiator: str = Field(min_length=1)


class RecruiterEvidenceOutput(BaseModel):
    title: str = Field(min_length=1)
    evidence: str = Field(min_length=1)


class RecruiterRiskOutput(BaseModel):
    issue: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class RecruiterImprovementOutput(BaseModel):
    action: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class RecruiterLensOutput(BaseModel):
    recruiter_snapshot: RecruiterSnapshotOutput
    first_impression: str = Field(min_length=1)
    clarity: str = Field(min_length=1)
    visible_strengths: list[RecruiterEvidenceOutput] = Field(default_factory=list)
    potentially_missed: list[RecruiterEvidenceOutput] = Field(default_factory=list)
    risks: list[RecruiterRiskOutput] = Field(default_factory=list)
    improvements: list[RecruiterImprovementOutput] = Field(default_factory=list)
    current_positioning: str = Field(min_length=1)
    recommended_positioning: str = Field(min_length=1)
    limitations: list[str] = Field(default_factory=list)

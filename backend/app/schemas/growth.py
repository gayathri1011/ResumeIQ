from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import sanitize_target_role


class CreateGrowthPlanRequest(BaseModel):
    resume_id: uuid.UUID | None = None
    resume_version_id: uuid.UUID | None = None
    target_role: str = Field(min_length=1, max_length=100)
    target_company: str | None = Field(default=None, max_length=100)

    @field_validator("target_role")
    @classmethod
    def validate_target_role(cls, value: str) -> str:
        return sanitize_target_role(value)


class SkillGapResponse(BaseModel):
    skill: str
    required_level: str = "advanced"
    current_level: str = "none"
    has_skill: bool = False
    evidence: list[str] = Field(default_factory=list)
    evidence_strength: str = "none"
    evidence_class: str = "missing"
    importance: str = "important"
    gap: str = "large"
    priority: str = "medium"
    status: str = "missing"
    gap_type: str = "missing_capability"
    why_it_matters: str = ""
    target_competency: str = ""
    verified_in_interview: bool = False
    latest_interview_score: int | None = None
    evidence_count: int = 0


class RoadmapMilestoneResponse(BaseModel):
    milestone_id: str
    title: str
    skill: str = ""
    why_it_matters: str = ""
    current_level: str = "none"
    target_level: str = "competent"
    priority: str = "medium"
    estimated_effort: str = "1-2 weeks"
    prerequisites: list[str] = Field(default_factory=list)
    recommended_action: str = ""
    practical_exercise: str = ""
    linked_project: str | None = None
    skills_addressed: list[str] = Field(default_factory=list)
    deliverable: str = ""
    status: str = "not_started"
    completed_at: datetime | None = None
    evidence_type: str | None = None
    notes: str | None = None


class RoadmapPhaseResponse(BaseModel):
    phase_number: int
    name: str
    duration_weeks: int = 4
    focus_skills: list[str] = Field(default_factory=list)
    milestones: list[RoadmapMilestoneResponse] = Field(default_factory=list)
    learning_objectives: list[str] = Field(default_factory=list)


class ProjectRecommendationResponse(BaseModel):
    project_id: str
    title: str
    description: str = ""
    why_this_project: str = ""
    gaps_addressed: list[str] = Field(default_factory=list)
    targeted_skills: list[str] = Field(default_factory=list)
    suggested_technologies: list[str] = Field(default_factory=list)
    difficulty: str = "intermediate"
    architecture_overview: str = ""
    what_to_implement: str = ""
    key_deliverables: list[str] = Field(default_factory=list)
    resume_evidence: str = ""
    resume_bullet_preview: str = ""


class EvidenceEventResponse(BaseModel):
    event_id: str
    source_type: str
    source_id: str
    idempotency_key: str
    skill: str
    score: int
    weight: float
    notes: str = ""
    recorded_at: datetime


class ChangeLogResponse(BaseModel):
    change_id: str
    timestamp: datetime
    change_type: str
    message: str
    affected_skills: list[str] = Field(default_factory=list)


class CareerGrowthPlanResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    resume_id: uuid.UUID | None = None
    resume_version_id: uuid.UUID | None = None
    target_role: str
    target_company: str | None = None
    readiness_score: int
    status: str
    summary: str | None = None
    skill_gaps: list[SkillGapResponse] = Field(default_factory=list)
    roadmap_phases: list[RoadmapPhaseResponse] = Field(default_factory=list)
    project_recommendations: list[ProjectRecommendationResponse] = Field(default_factory=list)
    evidence_events: list[EvidenceEventResponse] = Field(default_factory=list)
    change_logs: list[ChangeLogResponse] = Field(default_factory=list)
    last_evaluated_at: datetime | None = None
    created_at: datetime


class ReadinessOverviewResponse(BaseModel):
    target_role: str
    overall_readiness_score: int
    evidence_classes_summary: dict[str, int]
    priorities_summary: dict[str, int]
    skill_gaps: list[SkillGapResponse] = Field(default_factory=list)
    weighting_policy: dict[str, float] = Field(default_factory=dict)


class UpdateMilestoneStatusRequest(BaseModel):
    status: str = Field(pattern="^(not_started|in_progress|completed)$")
    evidence_type: str | None = Field(default="self_reported")
    notes: str | None = Field(default=None, max_length=1000)


class SyncInterviewResultResponse(BaseModel):
    plan_id: uuid.UUID
    session_id: uuid.UUID
    events_added: int
    updated_readiness_score: int
    affected_skills: list[str]
    message: str
    already_synced: bool

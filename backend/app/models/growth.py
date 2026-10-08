from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from pymongo import ASCENDING, DESCENDING, IndexModel

from app.core.database import MongoDocument
from app.models.enums import GrowthPlanStatus


class SkillGapRecord(BaseModel):
    skill: str
    required_level: str = "advanced"  # "beginner" | "competent" | "advanced" | "expert"
    current_level: str = "none"  # "none" | "beginner" | "competent" | "advanced" | "expert"
    has_skill: bool = False
    evidence: list[str] = Field(default_factory=list)
    evidence_strength: str = "none"  # "strong" | "moderate" | "weak" | "none"
    evidence_class: str = "missing"  # "evidence-backed" | "inferred" | "unverified" | "missing"
    importance: str = "important"  # "critical" | "important" | "beneficial"
    gap: str = "large"  # "none" | "small" | "medium" | "large"
    priority: str = "medium"  # "high" | "medium" | "low"
    status: str = "missing"  # "missing" | "in_progress" | "verified"
    gap_type: str = "missing_capability"  # "missing_capability" | "proof_gap"
    why_it_matters: str = ""
    target_competency: str = ""
    verified_in_interview: bool = False
    latest_interview_score: int | None = None
    evidence_count: int = 0


class RoadmapMilestone(BaseModel):
    milestone_id: str
    title: str
    skill: str = ""
    why_it_matters: str = ""
    current_level: str = "none"
    target_level: str = "competent"
    priority: str = "medium"  # "high" | "medium" | "low"
    estimated_effort: str = "1-2 weeks"  # Range: e.g. "1-2 weeks", "2-3 weeks", "3-4 weeks"
    prerequisites: list[str] = Field(default_factory=list)
    recommended_action: str = ""
    practical_exercise: str = ""
    linked_project: str | None = None
    skills_addressed: list[str] = Field(default_factory=list)
    deliverable: str = ""
    status: str = "not_started"  # "not_started" | "in_progress" | "completed"
    completed_at: datetime | None = None
    evidence_type: str | None = None  # "self_reported" | "verified_evidence" | "project_evidence" | "interview"
    notes: str | None = None


class RoadmapPhaseRecord(BaseModel):
    phase_number: int
    name: str
    duration_weeks: int = 4
    focus_skills: list[str] = Field(default_factory=list)
    milestones: list[RoadmapMilestone] = Field(default_factory=list)
    learning_objectives: list[str] = Field(default_factory=list)


class ProjectRecommendationRecord(BaseModel):
    project_id: str
    title: str
    description: str = ""
    why_this_project: str = ""
    gaps_addressed: list[str] = Field(default_factory=list)
    targeted_skills: list[str] = Field(default_factory=list)
    suggested_technologies: list[str] = Field(default_factory=list)
    difficulty: str = "intermediate"  # "beginner" | "intermediate" | "advanced"
    architecture_overview: str = ""
    what_to_implement: str = ""
    key_deliverables: list[str] = Field(default_factory=list)
    resume_evidence: str = ""
    resume_bullet_preview: str = ""


class EvidenceEvent(BaseModel):
    """Evidence event recording demonstrated capability with credibility weights.

    Weighting Rule:
    - 1.00: interview (Rigorous, live technical evaluation)
    - 0.75: project_evidence (Demonstrated working project repository)
    - 0.50: verified_evidence (Third-party credential or certification)
    - 0.15: self_reported (Self-completed roadmap milestone checkbox)
    """

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_type: str = "interview"  # "self_reported" | "verified_evidence" | "project_evidence" | "interview"
    source_id: str
    idempotency_key: str
    skill: str
    score: int = 0
    weight: float = 1.0
    notes: str = ""
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ChangeLogRecord(BaseModel):
    change_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    change_type: str = "plan_created"  # "interview_sync" | "milestone_update" | "plan_created" | "plan_refreshed"
    message: str
    affected_skills: list[str] = Field(default_factory=list)


class CareerGrowthPlan(MongoDocument):
    user_id: uuid.UUID
    resume_id: uuid.UUID | None = None
    resume_version_id: uuid.UUID | None = None
    target_role: str
    target_company: str | None = None
    readiness_score: int = 0  # 0-100 deterministic
    status: GrowthPlanStatus = GrowthPlanStatus.ACTIVE
    summary: str | None = None
    skill_gaps: list[SkillGapRecord] = Field(default_factory=list)
    roadmap_phases: list[RoadmapPhaseRecord] = Field(default_factory=list)
    project_recommendations: list[ProjectRecommendationRecord] = Field(default_factory=list)
    evidence_events: list[EvidenceEvent] = Field(default_factory=list)
    change_logs: list[ChangeLogRecord] = Field(default_factory=list)
    last_evaluated_at: datetime | None = None

    class Settings:
        name = "career_growth_plans"
        indexes = [
            IndexModel([("user_id", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("user_id", ASCENDING), ("target_role", ASCENDING)]),
        ]

    def __repr__(self) -> str:
        return f"<CareerGrowthPlan id={self.id} user_id={self.user_id} target_role={self.target_role!r} readiness={self.readiness_score}>"

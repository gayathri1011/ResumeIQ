"""Pydantic schemas for Career Growth Engine structured outputs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CareerSkillGapItem(BaseModel):
    skill: str = Field(min_length=1)
    priority: Literal["high", "medium", "low"] = Field(default="medium")
    gap_type: Literal["missing_capability", "proof_gap"] = Field(default="missing_capability")
    why_it_matters: str = Field(min_length=1)
    expected_competency: str = Field(min_length=1)
    importance: Literal["critical", "important", "beneficial"] = Field(default="important")
    required_level: Literal["beginner", "competent", "advanced", "expert"] = Field(default="advanced")


class CareerSkillGapOutput(BaseModel):
    target_role: str = Field(min_length=1)
    current_readiness_percentage: int = Field(ge=0, le=100)
    summary: str = Field(min_length=1)
    gaps: list[CareerSkillGapItem] = Field(default_factory=list)
    strengths_to_leverage: list[str] = Field(default_factory=list)

    @field_validator("gaps", "strengths_to_leverage", mode="before")
    @classmethod
    def default_empty_list(cls, value: list | None) -> list:
        return value or []


class RoadmapMilestoneOutput(BaseModel):
    milestone_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    skills_addressed: list[str] = Field(default_factory=list)
    deliverable: str = Field(default="")
    skill: str = Field(default="")
    why_it_matters: str = Field(default="")
    current_level: str = Field(default="none")
    target_level: str = Field(default="competent")
    priority: Literal["high", "medium", "low"] = Field(default="medium")
    estimated_effort: str = Field(default="1-2 weeks")
    prerequisites: list[str] = Field(default_factory=list)
    recommended_action: str = Field(default="")
    practical_exercise: str = Field(default="")
    linked_project: str | None = Field(default=None)

    @field_validator("skills_addressed", "prerequisites", mode="before")
    @classmethod
    def default_empty_list(cls, value: list | None) -> list:
        return value or []


class RoadmapPhaseOutput(BaseModel):
    phase_number: int = Field(ge=1)
    name: str = Field(min_length=1)
    duration_weeks: int = Field(default=4, ge=1, le=12)
    focus_skills: list[str] = Field(default_factory=list)
    milestones: list[RoadmapMilestoneOutput] = Field(default_factory=list)
    learning_objectives: list[str] = Field(default_factory=list)

    @field_validator("focus_skills", "milestones", "learning_objectives", mode="before")
    @classmethod
    def default_empty_list(cls, value: list | None) -> list:
        return value or []


class CareerRoadmapOutput(BaseModel):
    target_role: str = Field(min_length=1)
    estimated_duration_weeks: int = Field(default=12, ge=1, le=52)
    summary: str = Field(min_length=1)
    phases: list[RoadmapPhaseOutput] = Field(default_factory=list)

    @field_validator("phases", mode="before")
    @classmethod
    def default_empty_list(cls, value: list | None) -> list:
        return value or []


class RecommendedProjectOutput(BaseModel):
    project_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(default="")
    why_this_project: str = Field(default="")
    gaps_addressed: list[str] = Field(default_factory=list)
    targeted_skills: list[str] = Field(default_factory=list)
    suggested_technologies: list[str] = Field(default_factory=list)
    difficulty: Literal["beginner", "intermediate", "advanced"] = Field(default="intermediate")
    architecture_overview: str = Field(default="")
    what_to_implement: str = Field(default="")
    key_deliverables: list[str] = Field(default_factory=list)
    resume_evidence: str = Field(default="")
    resume_bullet_preview: str = Field(default="")

    @field_validator("targeted_skills", "gaps_addressed", "suggested_technologies", "key_deliverables", mode="before")
    @classmethod
    def default_empty_list(cls, value: list | None) -> list:
        return value or []


class ProjectRecommendationsOutput(BaseModel):
    target_role: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    projects: list[RecommendedProjectOutput] = Field(default_factory=list)

    @field_validator("projects", mode="before")
    @classmethod
    def default_empty_list(cls, value: list | None) -> list:
        return value or []

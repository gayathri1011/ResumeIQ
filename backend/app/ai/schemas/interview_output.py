"""Pydantic schemas for Adaptive AI Interviewer structured outputs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class RubricCriteria(BaseModel):
    criterion: str = Field(min_length=1)
    description: str = Field(min_length=1)
    weight: int = Field(default=20, ge=1, le=100)


class PlannedQuestion(BaseModel):
    topic: str = Field(min_length=1)
    skill_tag: str = Field(min_length=1)
    target_competency: str = Field(min_length=1)
    difficulty: str = Field(default="mid")


class InterviewPlanOutput(BaseModel):
    target_role: str = Field(min_length=1)
    difficulty: str = Field(default="mid")
    estimated_duration_minutes: int = Field(default=30, ge=10, le=90)
    domains: list[str] = Field(default_factory=list)
    focus_skills: list[str] = Field(default_factory=list)
    initial_question: str = Field(min_length=1)
    initial_skill_tag: str = Field(min_length=1)
    initial_expected_criteria: list[str] = Field(default_factory=list)
    rubric: list[RubricCriteria] = Field(default_factory=list)
    question_plan: list[PlannedQuestion] = Field(default_factory=list)

    @field_validator(
        "domains",
        "focus_skills",
        "initial_expected_criteria",
        "rubric",
        "question_plan",
        mode="before",
    )
    @classmethod
    def default_empty_list(cls, value: list | None) -> list:
        return value or []


class CriterionFeedback(BaseModel):
    criterion: str = Field(min_length=1)
    met: bool = Field(default=False)
    notes: str = Field(default="")


class SkillTagAssessment(BaseModel):
    skill: str = Field(min_length=1)
    demonstrated_level: str = Field(default="competent")  # "none" | "beginner" | "competent" | "advanced"
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class InterviewTurnEvalOutput(BaseModel):
    score: int = Field(default=7, ge=0, le=10)
    turn_score: int = Field(default=70, ge=0, le=100)
    dimension_scores: dict[str, int] = Field(default_factory=dict)
    criteria_feedback: list[CriterionFeedback] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    areas_for_improvement: list[str] = Field(default_factory=list)
    missing_points: list[str] = Field(default_factory=list)
    feedback: str = Field(default="")
    next_question_direction: str = Field(default="")
    resume_claim_status: str = Field(default="n/a")
    skill_tags: list[str] = Field(default_factory=list)
    skill_tag_assessments: list[SkillTagAssessment] = Field(default_factory=list)
    next_action: Literal["follow_up", "next_topic", "wrap_up"] = Field(default="next_topic")
    next_question: str | None = Field(default=None)
    next_skill_tag: str | None = Field(default=None)
    interviewer_rationale: str = Field(default="")

    @field_validator(
        "criteria_feedback",
        "strengths",
        "areas_for_improvement",
        "missing_points",
        "skill_tags",
        "skill_tag_assessments",
        mode="before",
    )
    @classmethod
    def default_empty_list(cls, value: list | None) -> list:
        return value or []

    @model_validator(mode="before")
    @classmethod
    def sync_turn_eval_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        copied = dict(data)
        if "turn_score" in copied and "score" not in copied:
            copied["score"] = max(0, min(10, round(copied["turn_score"] / 10)))
        elif "score" in copied and "turn_score" not in copied:
            copied["turn_score"] = int(copied["score"]) * 10
        if not copied.get("missing_points") and copied.get("areas_for_improvement"):
            copied["missing_points"] = list(copied["areas_for_improvement"])
        if not copied.get("feedback") and copied.get("interviewer_rationale"):
            copied["feedback"] = copied["interviewer_rationale"]
        if not copied.get("skill_tags") and copied.get("skill_tag_assessments"):
            copied["skill_tags"] = [
                a.get("skill", "") if isinstance(a, dict) else getattr(a, "skill", "")
                for a in copied["skill_tag_assessments"]
                if (isinstance(a, dict) and a.get("skill")) or getattr(a, "skill", None)
            ]
        return copied


class InterviewSkillScore(BaseModel):
    skill: str = Field(min_length=1)
    score: int = Field(ge=0, le=100)
    evidence_summary: str = Field(min_length=1)


class InterviewReportOutput(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    readiness_level: str = Field(default="interview_ready")  # "needs_work" | "progressing" | "interview_ready" | "strong_fit"
    readiness_status: str = Field(default="interview_ready")
    summary: str = Field(min_length=1)
    category_scores: dict[str, int] = Field(default_factory=dict)
    demonstrated_strengths: list[str] = Field(default_factory=list)
    strong_areas: list[str] = Field(default_factory=list)
    verified_gaps: list[str] = Field(default_factory=list)
    weak_areas: list[str] = Field(default_factory=list)
    resume_claims_tested: list[dict[str, Any]] = Field(default_factory=list)
    skill_evaluations: list[InterviewSkillScore] = Field(default_factory=list)
    key_recommendations: list[str] = Field(default_factory=list)
    actionable_recommendations: list[str] = Field(default_factory=list)
    ordered_next_practice_areas: list[str] = Field(default_factory=list)

    @field_validator(
        "demonstrated_strengths",
        "strong_areas",
        "verified_gaps",
        "weak_areas",
        "resume_claims_tested",
        "skill_evaluations",
        "key_recommendations",
        "actionable_recommendations",
        "ordered_next_practice_areas",
        mode="before",
    )
    @classmethod
    def default_empty_list(cls, value: list | None) -> list:
        return value or []

    @field_validator("category_scores", mode="before")
    @classmethod
    def default_empty_dict(cls, value: dict | None) -> dict:
        return value or {}

    @model_validator(mode="before")
    @classmethod
    def sync_report_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        copied = dict(data)
        if not copied.get("strong_areas") and copied.get("demonstrated_strengths"):
            copied["strong_areas"] = list(copied["demonstrated_strengths"])
        elif not copied.get("demonstrated_strengths") and copied.get("strong_areas"):
            copied["demonstrated_strengths"] = list(copied["strong_areas"])

        if not copied.get("weak_areas") and copied.get("verified_gaps"):
            copied["weak_areas"] = list(copied["verified_gaps"])
        elif not copied.get("verified_gaps") and copied.get("weak_areas"):
            copied["verified_gaps"] = list(copied["weak_areas"])

        if not copied.get("actionable_recommendations") and copied.get("key_recommendations"):
            copied["actionable_recommendations"] = list(copied["key_recommendations"])
        elif not copied.get("key_recommendations") and copied.get("actionable_recommendations"):
            copied["key_recommendations"] = list(copied["actionable_recommendations"])

        if not copied.get("readiness_status") and copied.get("readiness_level"):
            copied["readiness_status"] = copied["readiness_level"]
        elif not copied.get("readiness_level") and copied.get("readiness_status"):
            copied["readiness_level"] = copied["readiness_status"]
        return copied


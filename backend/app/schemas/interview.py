from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.common import sanitize_target_role


class CreateInterviewSessionRequest(BaseModel):
    resume_id: uuid.UUID | None = None
    resume_version_id: uuid.UUID | None = None
    job_description_id: uuid.UUID | None = None
    job_description_text: str | None = Field(default=None, max_length=15000)
    target_role: str = Field(min_length=1, max_length=100)
    difficulty: str = Field(default="mid")
    interview_type: str = Field(default="technical")
    estimated_question_count: int = Field(default=5, ge=1, le=10)
    focus_areas: list[str] = Field(default_factory=list)
    focus_skills: list[str] = Field(default_factory=list)

    @field_validator("resume_id", "resume_version_id", "job_description_id", mode="before")
    @classmethod
    def coerce_empty_uuid_to_none(cls, value: Any) -> Any:
        if not value or str(value).strip() in ("", "none", "null", "undefined"):
            return None
        try:
            return uuid.UUID(str(value))
        except (ValueError, TypeError, AttributeError):
            return None

    @field_validator("estimated_question_count", mode="before")
    @classmethod
    def coerce_question_count(cls, value: Any) -> int:
        if value is None or value == "":
            return 5
        try:
            val = int(value)
            return max(1, min(10, val))
        except (ValueError, TypeError):
            return 5

    @field_validator("target_role")
    @classmethod
    def validate_target_role(cls, value: str) -> str:
        return sanitize_target_role(value)


class InterviewTurnResponse(BaseModel):
    turn_index: int
    question: str
    category: str = "technical fundamentals"
    difficulty: str = "mid"
    skill_tag: str
    skill_tags: list[str] = Field(default_factory=list)
    user_answer: str | None = None
    turn_score: int | None = None
    evaluation: dict[str, Any] | None = None
    is_follow_up: bool = False
    answered_at: datetime | None = None


class InterviewSessionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    resume_id: uuid.UUID | None = None
    job_description_id: uuid.UUID | None = None
    target_role: str
    difficulty: str
    interview_type: str
    status: str
    plan: dict[str, Any] | None = None
    current_turn_index: int = 0
    turns: list[InterviewTurnResponse] = Field(default_factory=list)
    current_question: str | None = None
    overall_score: int | None = None
    report: dict[str, Any] | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class InterviewSessionListItem(BaseModel):
    id: uuid.UUID
    target_role: str
    difficulty: str
    status: str
    overall_score: int | None = None
    total_turns: int = 0
    turns_count: int = 0
    answered_turns: int = 0
    main_strengths: list[str] = Field(default_factory=list)
    top_strengths: list[str] = Field(default_factory=list)
    main_weaknesses: list[str] = Field(default_factory=list)
    primary_gaps: list[str] = Field(default_factory=list)
    readiness_status: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def sync_list_item_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        copied = dict(data)
        if not copied.get("turns_count") and copied.get("total_turns"):
            copied["turns_count"] = copied["total_turns"]
        elif not copied.get("total_turns") and copied.get("turns_count"):
            copied["total_turns"] = copied["turns_count"]

        if not copied.get("top_strengths") and copied.get("main_strengths"):
            copied["top_strengths"] = list(copied["main_strengths"])
        elif not copied.get("main_strengths") and copied.get("top_strengths"):
            copied["main_strengths"] = list(copied["top_strengths"])

        if not copied.get("primary_gaps") and copied.get("main_weaknesses"):
            copied["primary_gaps"] = list(copied["main_weaknesses"])
        elif not copied.get("main_weaknesses") and copied.get("primary_gaps"):
            copied["main_weaknesses"] = list(copied["primary_gaps"])
        return copied


class SubmitAnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=5000)


class TurnEvaluationResponse(BaseModel):
    turn_index: int
    score: int = Field(ge=0, le=10)
    dimension_scores: dict[str, int] = Field(default_factory=dict)
    strengths: list[str] = Field(default_factory=list)
    missing_points: list[str] = Field(default_factory=list)
    feedback: str = ""
    next_question_direction: str = ""
    resume_claim_status: str = "n/a"
    skill_tags: list[str] = Field(default_factory=list)
    is_complete: bool = False
    next_turn: InterviewTurnResponse | None = None


class InterviewReportResponse(BaseModel):
    session_id: uuid.UUID
    target_role: str
    difficulty: str
    overall_score: int = Field(ge=0, le=100)
    readiness_status: str
    summary: str
    category_scores: dict[str, int] = Field(default_factory=dict)
    strong_areas: list[str] = Field(default_factory=list)
    weak_areas: list[str] = Field(default_factory=list)
    resume_claims_tested: list[dict[str, Any]] = Field(default_factory=list)
    actionable_recommendations: list[str] = Field(default_factory=list)
    ordered_next_practice_areas: list[str] = Field(default_factory=list)
    ordered_practice_areas: list[str] = Field(default_factory=list)
    skill_evaluations: list[dict[str, Any]] = Field(default_factory=list)
    skill_scores: dict[str, int] = Field(default_factory=dict)
    turns_evaluated: int = 0
    completed_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def sync_report_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        copied = dict(data)
        if "session_id" not in copied and "id" in copied:
            copied["session_id"] = copied["id"]

        if copied.get("overall_score") is None:
            copied["overall_score"] = 0
        else:
            try:
                copied["overall_score"] = max(0, min(100, int(copied["overall_score"])))
            except (ValueError, TypeError):
                copied["overall_score"] = 0

        if not copied.get("readiness_status"):
            score = copied["overall_score"]
            copied["readiness_status"] = "interview_ready" if score >= 75 else ("progressing" if score >= 60 else "needs_work")

        if not copied.get("summary"):
            copied["summary"] = f"Interview session completed for {copied.get('target_role', 'your role')}."

        if not copied.get("target_role"):
            copied["target_role"] = "Software Engineer"

        if not copied.get("difficulty"):
            copied["difficulty"] = "mid"

        if not copied.get("ordered_practice_areas") and copied.get("ordered_next_practice_areas"):
            copied["ordered_practice_areas"] = list(copied["ordered_next_practice_areas"])
        elif not copied.get("ordered_next_practice_areas") and copied.get("ordered_practice_areas"):
            copied["ordered_next_practice_areas"] = list(copied["ordered_practice_areas"])

        for list_field in (
            "strong_areas",
            "weak_areas",
            "resume_claims_tested",
            "actionable_recommendations",
            "ordered_next_practice_areas",
            "ordered_practice_areas",
            "skill_evaluations",
        ):
            if copied.get(list_field) is None:
                copied[list_field] = []

        for dict_field in ("category_scores", "skill_scores"):
            if copied.get(dict_field) is None:
                copied[dict_field] = {}

        if not copied.get("skill_scores") and copied.get("skill_evaluations"):
            copied["skill_scores"] = {
                item.get("skill", ""): int(item.get("score", 70))
                for item in copied["skill_evaluations"]
                if isinstance(item, dict) and item.get("skill")
            }
        return copied

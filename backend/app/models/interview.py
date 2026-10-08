from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from pymongo import ASCENDING, DESCENDING, IndexModel

from app.core.database import MongoDocument
from app.models.enums import InterviewStatus


class InterviewTurn(BaseModel):
    turn_index: int
    question: str
    skill_tag: str
    category: str = "technical fundamentals"
    skill_tags: list[str] = Field(default_factory=list)
    question_type: str = "technical"
    difficulty: str = "mid"
    expected_criteria: list[str] = Field(default_factory=list)
    user_answer: str | None = None
    answered_at: datetime | None = None
    turn_score: int | None = None
    evaluation: dict[str, Any] | None = None
    is_follow_up: bool = False
    follow_up_depth: int = 0
    strengths: list[str] = Field(default_factory=list)
    areas_for_improvement: list[str] = Field(default_factory=list)
    criteria_feedback: list[dict[str, Any]] = Field(default_factory=list)
    next_action: str | None = None
    interviewer_notes: str | None = None


class InterviewSession(MongoDocument):
    user_id: uuid.UUID
    resume_id: uuid.UUID | None = None
    resume_version_id: uuid.UUID | None = None
    job_description_id: uuid.UUID | None = None
    job_description_text: str | None = None
    target_role: str
    difficulty: str = "mid"
    interview_type: str = "technical"
    estimated_question_count: int = 5
    focus_areas: list[str] = Field(default_factory=list)
    focus_skills: list[str] = Field(default_factory=list)
    status: InterviewStatus = InterviewStatus.SETUP
    plan: dict[str, Any] | None = None
    turns: list[InterviewTurn] = Field(default_factory=list)
    current_turn_index: int = 0
    report: dict[str, Any] | None = None
    overall_score: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    class Settings:
        name = "interview_sessions"
        indexes = [
            IndexModel([("user_id", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("resume_id", ASCENDING)]),
            IndexModel([("job_description_id", ASCENDING)]),
        ]

    def __repr__(self) -> str:
        return f"<InterviewSession id={self.id} user_id={self.user_id} role={self.target_role!r} status={self.status}>"

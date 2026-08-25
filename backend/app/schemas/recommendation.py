import uuid
from typing import Any

from pydantic import Field

from app.models.enums import RecommendationSourceType
from app.schemas.common import BaseSchema, TimestampSchema


class RecommendationCreate(BaseSchema):
    resume_id: uuid.UUID
    source_type: RecommendationSourceType
    resume_analysis_id: uuid.UUID | None = None
    job_match_id: uuid.UUID | None = None
    priority: int = 0
    category: str | None = Field(default=None, max_length=128)
    title: str = Field(min_length=1, max_length=512)
    explanation: str | None = None
    impact: str | None = Field(default=None, max_length=64)
    suggested_action: str | None = None
    action_items: list[Any] | None = None


class RecommendationUpdate(BaseSchema):
    priority: int | None = None
    category: str | None = Field(default=None, max_length=128)
    title: str | None = Field(default=None, min_length=1, max_length=512)
    explanation: str | None = None
    impact: str | None = Field(default=None, max_length=64)
    suggested_action: str | None = None
    action_items: list[Any] | None = None


class RecommendationRead(TimestampSchema):
    id: uuid.UUID
    resume_id: uuid.UUID
    source_type: RecommendationSourceType
    resume_analysis_id: uuid.UUID | None
    job_match_id: uuid.UUID | None
    priority: int
    category: str | None
    title: str
    explanation: str | None
    impact: str | None
    suggested_action: str | None
    action_items: list[Any] | None

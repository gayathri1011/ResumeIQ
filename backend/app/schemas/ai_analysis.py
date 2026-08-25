import uuid
from typing import Any

from pydantic import Field

from app.models.enums import AIResultType, AIServiceName
from app.schemas.common import BaseSchema, TimestampSchema


class AIAnalysisResultCreate(BaseSchema):
    service_name: AIServiceName
    input_hash: str = Field(min_length=1, max_length=64)
    result_type: AIResultType
    payload: dict[str, Any]
    model_used: str | None = Field(default=None, max_length=128)
    prompt_version: str | None = Field(default=None, max_length=64)
    token_usage: dict[str, Any] | None = None
    resume_id: uuid.UUID | None = None
    resume_version_id: uuid.UUID | None = None
    resume_analysis_id: uuid.UUID | None = None
    job_description_id: uuid.UUID | None = None
    job_match_id: uuid.UUID | None = None


class AIAnalysisResultRead(TimestampSchema):
    id: uuid.UUID
    service_name: AIServiceName
    input_hash: str
    result_type: AIResultType
    payload: dict[str, Any]
    model_used: str | None
    prompt_version: str | None
    token_usage: dict[str, Any] | None
    resume_id: uuid.UUID | None
    resume_version_id: uuid.UUID | None
    resume_analysis_id: uuid.UUID | None
    job_description_id: uuid.UUID | None
    job_match_id: uuid.UUID | None

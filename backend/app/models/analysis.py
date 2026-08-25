from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pymongo import ASCENDING, DESCENDING, IndexModel

from app.core.database import MongoDocument
from app.models.enums import AIResultType, AIServiceName, AnalysisStatus, RecommendationSourceType


class ResumeAnalysis(MongoDocument):
    resume_id: uuid.UUID
    resume_version_id: uuid.UUID | None = None
    overall_score: int | None = None
    category_scores: dict[str, Any] | None = None
    issues: list[Any] | None = None
    status: AnalysisStatus = AnalysisStatus.PENDING
    analyzed_at: datetime | None = None

    class Settings:
        name = "resume_analyses"
        indexes = [
            IndexModel([("resume_id", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("resume_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("resume_version_id", ASCENDING)]),
        ]

    def __repr__(self) -> str:
        return f"<ResumeAnalysis id={self.id} resume_id={self.resume_id} status={self.status}>"


class Recommendation(MongoDocument):
    resume_id: uuid.UUID
    source_type: RecommendationSourceType
    resume_analysis_id: uuid.UUID | None = None
    job_match_id: uuid.UUID | None = None
    priority: int = 0
    category: str | None = None
    title: str
    explanation: str | None = None
    impact: str | None = None
    suggested_action: str | None = None
    action_items: list[Any] | None = None

    class Settings:
        name = "recommendations"
        indexes = [
            IndexModel([("resume_id", ASCENDING), ("priority", ASCENDING)]),
            IndexModel([("job_match_id", ASCENDING), ("category", ASCENDING)]),
            IndexModel([("resume_analysis_id", ASCENDING)]),
        ]

    def __repr__(self) -> str:
        return f"<Recommendation id={self.id} title={self.title!r}>"


class AIAnalysisResult(MongoDocument):
    service_name: AIServiceName
    input_hash: str
    result_type: AIResultType
    payload: dict[str, Any]
    model_used: str | None = None
    prompt_version: str | None = None
    token_usage: dict[str, Any] | None = None
    resume_id: uuid.UUID | None = None
    resume_version_id: uuid.UUID | None = None
    resume_analysis_id: uuid.UUID | None = None
    job_description_id: uuid.UUID | None = None
    job_match_id: uuid.UUID | None = None

    class Settings:
        name = "ai_analysis_results"
        indexes = [
            IndexModel([("input_hash", ASCENDING), ("service_name", ASCENDING)]),
            IndexModel([("resume_id", ASCENDING), ("service_name", ASCENDING), ("result_type", ASCENDING)]),
            IndexModel([("resume_analysis_id", ASCENDING)]),
            IndexModel([("job_match_id", ASCENDING)]),
        ]

    def __repr__(self) -> str:
        return f"<AIAnalysisResult id={self.id} service={self.service_name}>"

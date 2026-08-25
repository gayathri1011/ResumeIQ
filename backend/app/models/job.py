from __future__ import annotations

import uuid
from typing import Any

from pymongo import ASCENDING, DESCENDING, IndexModel

from app.core.database import MongoDocument


class JobDescription(MongoDocument):
    user_id: uuid.UUID | None = None
    title: str
    company: str | None = None
    raw_text: str
    parsed_requirements: dict[str, Any] | None = None
    content_embedding: list[float] | None = None

    class Settings:
        name = "job_descriptions"
        indexes = [
            IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)]),
        ]

    def __repr__(self) -> str:
        return f"<JobDescription id={self.id} title={self.title!r}>"


class JobMatch(MongoDocument):
    resume_id: uuid.UUID
    resume_version_id: uuid.UUID | None = None
    job_description_id: uuid.UUID
    match_score: int
    semantic_score: float | None = None
    keyword_score: float | None = None
    breakdown: dict[str, Any] | None = None
    matched_skills: list[Any] | None = None
    missing_skills: list[Any] | None = None
    missing_keywords: list[Any] | None = None

    class Settings:
        name = "job_matches"
        indexes = [
            IndexModel([("resume_id", ASCENDING), ("job_description_id", ASCENDING)]),
            IndexModel([("resume_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("resume_version_id", ASCENDING)]),
        ]

    def __repr__(self) -> str:
        return f"<JobMatch id={self.id} score={self.match_score}>"

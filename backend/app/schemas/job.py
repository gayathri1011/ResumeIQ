import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import BaseSchema, TimestampSchema


class ExperienceRequirementsRead(BaseSchema):
    years_min: int | None = None
    years_max: int | None = None
    seniority_level: str | None = None
    description: str | None = None


class AnalyzeJobRequest(BaseSchema):
    raw_text: str = Field(min_length=1)
    company: str | None = Field(default=None, max_length=255)
    resume_id: uuid.UUID | None = None
    resume_version_id: uuid.UUID | None = None


class AnalyzeJobResponse(BaseSchema):
    id: uuid.UUID
    cached: bool
    job_title: str | None = None
    company: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    experience_requirements: ExperienceRequirementsRead | None = None
    education_requirements: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    target_resume_id: str | None = None
    target_resume_version_id: str | None = None
    analyzed_at: datetime | None = None
    prompt_version: str
    has_embedding: bool = False


class JobDescriptionListItem(BaseSchema):
    id: uuid.UUID
    title: str
    company: str | None
    job_title: str | None = None
    created_at: datetime
    updated_at: datetime
    has_embedding: bool = False
    required_skills_count: int = 0


class JobDescriptionDetailResponse(AnalyzeJobResponse):
    raw_text: str


class JobDescriptionCreate(BaseSchema):
    user_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    raw_text: str = Field(min_length=1)
    parsed_requirements: dict[str, Any] | None = None


class JobDescriptionUpdate(BaseSchema):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    raw_text: str | None = Field(default=None, min_length=1)
    parsed_requirements: dict[str, Any] | None = None


class JobDescriptionRead(TimestampSchema):
    id: uuid.UUID
    user_id: uuid.UUID | None
    title: str
    company: str | None
    raw_text: str
    parsed_requirements: dict[str, Any] | None


class JobMatchCreate(BaseSchema):
    resume_id: uuid.UUID
    resume_version_id: uuid.UUID | None = None
    job_description_id: uuid.UUID
    match_score: int = Field(ge=0, le=100)
    semantic_score: float | None = None
    keyword_score: float | None = None
    breakdown: dict[str, Any] | None = None
    matched_skills: list[Any] | None = None
    missing_skills: list[Any] | None = None
    missing_keywords: list[Any] | None = None


class JobMatchUpdate(BaseSchema):
    match_score: int | None = Field(default=None, ge=0, le=100)
    semantic_score: float | None = None
    keyword_score: float | None = None
    breakdown: dict[str, Any] | None = None
    matched_skills: list[Any] | None = None
    missing_skills: list[Any] | None = None
    missing_keywords: list[Any] | None = None


class JobMatchRead(TimestampSchema):
    id: uuid.UUID
    resume_id: uuid.UUID
    resume_version_id: uuid.UUID | None
    job_description_id: uuid.UUID
    match_score: int
    semantic_score: float | None
    keyword_score: float | None
    breakdown: dict[str, Any] | None
    matched_skills: list[Any] | None
    missing_skills: list[Any] | None
    missing_keywords: list[Any] | None


class MatchJobRequest(BaseSchema):
    resume_id: uuid.UUID
    resume_version_id: uuid.UUID | None = None


class MatchBreakdownRead(BaseSchema):
    skills_match: int
    experience_match: int
    keyword_match: int
    project_relevance: int
    education_match: int


class MatchExplanationRead(BaseSchema):
    category: str
    summary: str


class MatchJobResponse(BaseSchema):
    match_id: uuid.UUID
    cached: bool
    resume_id: uuid.UUID
    resume_version_id: uuid.UUID | None = None
    job_description_id: uuid.UUID
    job_title: str | None = None
    company: str | None = None
    match_score: int
    semantic_score: float | None = None
    keyword_score: float | None = None
    breakdown: MatchBreakdownRead
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    explanations: list[MatchExplanationRead] = Field(default_factory=list)
    summary: str = ""
    matched_at: datetime | None = None
    prompt_version: str = "job_match_v1"


class ResumeJobMatchListItem(BaseSchema):
    match_id: uuid.UUID
    resume_id: uuid.UUID
    resume_version_id: uuid.UUID | None = None
    job_description_id: uuid.UUID
    job_title: str | None = None
    company: str | None = None
    match_score: int
    semantic_score: float | None = None
    keyword_score: float | None = None
    breakdown: MatchBreakdownRead | None = None
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    summary: str = ""
    matched_at: datetime | None = None

"""Pydantic schemas for structured AI job match output."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class MatchBreakdown(BaseModel):
    skills_match: int = Field(ge=0, le=100)
    experience_match: int = Field(ge=0, le=100)
    keyword_match: int = Field(ge=0, le=100)
    project_relevance: int = Field(ge=0, le=100)
    education_match: int = Field(ge=0, le=100)


class MatchExplanation(BaseModel):
    category: str = Field(min_length=1)
    summary: str = Field(min_length=1)


class JobMatchOutput(BaseModel):
    breakdown: MatchBreakdown
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    explanations: list[MatchExplanation] = Field(default_factory=list)
    summary: str = Field(min_length=1)

    @field_validator("matched_skills", "missing_skills", "missing_keywords", mode="before")
    @classmethod
    def empty_list_if_null(cls, value: list[str] | None) -> list[str]:
        return value or []

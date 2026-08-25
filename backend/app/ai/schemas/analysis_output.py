"""Pydantic schemas for structured AI analysis output."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

DIMENSION_KEYS = [
    "ats_compatibility",
    "skills",
    "experience",
    "projects",
    "education",
    "certifications",
    "achievements",
    "professional_summary",
    "keywords",
    "content_quality",
    "readability",
    "relevance",
    "quantifiable_achievements",
    "action_verbs",
    "formatting_issues",
]

TOP_LEVEL_CATEGORY_KEYS = [
    "ats",
    "skills",
    "experience",
    "projects",
    "education",
    "keywords",
    "content_quality",
]

DIMENSION_TO_CATEGORY: dict[str, str] = {
    "ats_compatibility": "ats",
    "skills": "skills",
    "experience": "experience",
    "projects": "projects",
    "education": "education",
    "keywords": "keywords",
    "content_quality": "content_quality",
}


class DimensionScore(BaseModel):
    key: str
    score: int = Field(ge=0, le=100)
    explanation: str = Field(min_length=1)
    disclaimer: str | None = None

    @field_validator("key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        if value not in DIMENSION_KEYS:
            raise ValueError(f"Unknown dimension key: {value}")
        return value


class AnalysisIssue(BaseModel):
    severity: Literal["low", "medium", "high"]
    category: str
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    suggested_fix: str | None = None
    grounded_in_resume: bool = True


class ResumeAnalysisOutput(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    summary: str = Field(min_length=1)
    dimensions: list[DimensionScore] = Field(min_length=len(DIMENSION_KEYS), max_length=len(DIMENSION_KEYS))
    issues: list[AnalysisIssue] = Field(default_factory=list)

    @property
    def category_scores(self) -> dict[str, int]:
        scores: dict[str, int] = {}
        for dimension in self.dimensions:
            category = DIMENSION_TO_CATEGORY.get(dimension.key)
            if category:
                scores[category] = dimension.score
        return scores

    def get_dimension(self, key: str) -> DimensionScore | None:
        for dimension in self.dimensions:
            if dimension.key == key:
                return dimension
        return None

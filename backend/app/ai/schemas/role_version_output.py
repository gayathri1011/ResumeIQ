"""Pydantic schemas for role-specific resume version transformation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.ai.schemas.optimize_output import OptimizationChangeOutput


class TransformationInsightSection(BaseModel):
    section: str = Field(min_length=1)
    headline: str = Field(min_length=1)
    explanation: str = Field(min_length=1)


class TransformationInsights(BaseModel):
    summary: str = Field(min_length=1)
    sections: list[TransformationInsightSection] = Field(default_factory=list)
    top_strengths: list[str] = Field(default_factory=list)
    recommended_improvements: list[str] = Field(default_factory=list)


class JobMatchDetails(BaseModel):
    match_score: int | None = None
    matched_requirements: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    explanation: str = ""


class RoleVersionTransformOutput(BaseModel):
    optimized_content: dict[str, Any]
    changes: list[OptimizationChangeOutput] = Field(default_factory=list)
    insights: TransformationInsights
    role_relevance_score: int = Field(ge=0, le=100)
    ats_score: int = Field(ge=0, le=100)
    job_match_details: JobMatchDetails = Field(default_factory=JobMatchDetails)

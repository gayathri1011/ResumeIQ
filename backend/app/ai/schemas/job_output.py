"""Pydantic schemas for structured AI job description extraction output."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ExperienceRequirements(BaseModel):
    years_min: int | None = Field(default=None, ge=0)
    years_max: int | None = Field(default=None, ge=0)
    seniority_level: str | None = None
    description: str | None = None


class JobDescriptionExtractionOutput(BaseModel):
    job_title: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    experience_requirements: ExperienceRequirements | None = None
    education_requirements: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)

    @field_validator(
        "required_skills",
        "preferred_skills",
        "education_requirements",
        "tools",
        "technologies",
        "responsibilities",
        "keywords",
        mode="before",
    )
    @classmethod
    def empty_list_if_null(cls, value: list[str] | None) -> list[str]:
        return value or []

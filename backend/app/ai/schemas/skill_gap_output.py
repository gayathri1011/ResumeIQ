"""Pydantic schemas for AI skill gap enrichment output."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class MissingSkillExplanation(BaseModel):
    skill: str = Field(min_length=1)
    why_it_matters: str = Field(min_length=1)


class RoadmapStep(BaseModel):
    skill: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class SkillGapAIOutput(BaseModel):
    missing_skill_explanations: list[MissingSkillExplanation] = Field(default_factory=list)
    learning_roadmap: list[RoadmapStep] = Field(default_factory=list)

    @field_validator("missing_skill_explanations", "learning_roadmap", mode="before")
    @classmethod
    def empty_list_if_null(cls, value: list | None) -> list:
        return value or []

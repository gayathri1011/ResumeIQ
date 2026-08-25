"""Pydantic schemas for AI bullet improvement output."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

METRIC_PLACEHOLDER_PATTERN = re.compile(r"\[add [^\]]+\]", re.IGNORECASE)
NUMBER_PATTERN = re.compile(r"\b\d+(?:\.\d+)?%?\b")


class BulletImprovementOutput(BaseModel):
    improved_text: str = Field(min_length=1)
    changes_summary: str = Field(min_length=1)
    metric_placeholder_used: bool = False
    suggested_metric_prompt: str | None = None

    @field_validator("improved_text", "changes_summary")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


def extract_quantifiers(text: str) -> set[str]:
    cleaned = METRIC_PLACEHOLDER_PATTERN.sub("", text)
    return set(NUMBER_PATTERN.findall(cleaned))


def find_fabricated_metrics(
    original: str,
    improved: str,
    *,
    resume_context: str = "",
) -> set[str]:
    allowed = extract_quantifiers(original) | extract_quantifiers(resume_context)
    improved_numbers = extract_quantifiers(improved)
    return improved_numbers - allowed

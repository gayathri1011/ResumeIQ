"""Shared metric validation helpers for AI-generated resume content."""

from __future__ import annotations

import re

METRIC_PLACEHOLDER_PATTERN = re.compile(r"\[add [^\]]+\]", re.IGNORECASE)
NUMBER_PATTERN = re.compile(r"\b\d+(?:\.\d+)?%?\b")


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
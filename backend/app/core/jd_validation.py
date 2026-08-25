"""Job description validation helpers."""

from __future__ import annotations

from app.core.exceptions import AppError

MIN_JD_WORD_COUNT = 30


def validate_job_description_text(raw_text: str) -> str:
    """Validate pasted JD text; return stripped text on success."""
    stripped = raw_text.strip()
    if not stripped:
        raise AppError(
            "Job description cannot be empty. Paste the full job posting text.",
            code="jd_empty",
            status_code=422,
        )

    word_count = len(stripped.split())
    if word_count < MIN_JD_WORD_COUNT:
        raise AppError(
            "This doesn't look like a job description. Please paste a fuller posting "
            f"(at least {MIN_JD_WORD_COUNT} words).",
            code="jd_too_short",
            status_code=422,
        )

    return stripped

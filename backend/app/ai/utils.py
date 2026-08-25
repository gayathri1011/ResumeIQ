"""AI utility helpers."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID


def hash_resume_content(parsed_structure: dict[str, Any] | None) -> str:
    """Stable SHA-256 hash of parsed resume content (excludes upload metadata)."""
    if not parsed_structure:
        return hashlib.sha256(b"").hexdigest()

    content = {k: v for k, v in parsed_structure.items() if k != "_meta"}
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def normalize_job_text(raw_text: str) -> str:
    """Collapse whitespace for stable hashing and embedding input."""
    return " ".join(raw_text.strip().split())


def hash_job_text(raw_text: str) -> str:
    """Stable SHA-256 hash of normalized job description text."""
    normalized = normalize_job_text(raw_text).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def hash_match_inputs(
    resume_content_hash: str,
    job_content_hash: str,
    resume_version_id: UUID | str | None,
) -> str:
    """Stable hash for resume+JD+version match dedup."""
    payload = f"{resume_content_hash}:{job_content_hash}:{resume_version_id or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def hash_optimization_inputs(
    resume_content_hash: str,
    target_role: str,
    job_id: UUID | str | None = None,
    *,
    inline_context_hash: str | None = None,
) -> str:
    """Stable hash for resume optimization dedup."""
    normalized_role = " ".join(target_role.lower().strip().split())
    payload = (
        f"{resume_content_hash}:optimize:{normalized_role}:"
        f"{job_id or ''}:{inline_context_hash or ''}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

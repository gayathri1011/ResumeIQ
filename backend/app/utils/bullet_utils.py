"""Utilities for locating and updating bullets in parsed resume structures."""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from app.core.exceptions import AppError

BulletSection = Literal["experience", "projects"]


def split_description_bullets(description: str | None) -> list[str]:
    if not description:
        return []
    lines = [line.strip() for line in description.split("\n") if line.strip()]
    bullets: list[str] = []
    for line in lines:
        cleaned = re.sub(r"^[-*•]\s*", "", line).strip()
        if cleaned:
            bullets.append(cleaned)
    return bullets


def join_description_bullets(bullets: list[str]) -> str:
    return "\n".join(bullets)


def list_resume_bullets(parsed_structure: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not parsed_structure:
        return []

    items: list[dict[str, Any]] = []
    for section in ("experience", "projects"):
        entries = parsed_structure.get(section) or []
        for entry_index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            bullets = split_description_bullets(entry.get("description"))
            if not bullets and entry.get("description"):
                bullets = [str(entry["description"]).strip()]

            for bullet_index, text in enumerate(bullets):
                items.append(
                    {
                        "section": section,
                        "entry_index": entry_index,
                        "bullet_index": bullet_index,
                        "entry_title": entry.get("title"),
                        "organization": entry.get("organization"),
                        "text": text,
                    }
                )
    return items


def replace_resume_bullet(
    parsed_structure: dict[str, Any],
    *,
    section: BulletSection,
    entry_index: int,
    bullet_index: int,
    new_text: str,
) -> dict[str, Any]:
    updated = dict(parsed_structure)
    entries = list(updated.get(section) or [])
    if entry_index < 0 or entry_index >= len(entries):
        raise AppError("Resume entry not found.", code="bullet_location_not_found", status_code=404)

    entry = dict(entries[entry_index])
    bullets = split_description_bullets(entry.get("description"))
    if not bullets and entry.get("description"):
        bullets = [str(entry["description"]).strip()]

    if bullet_index < 0 or bullet_index >= len(bullets):
        raise AppError("Bullet not found.", code="bullet_not_found", status_code=404)

    bullets[bullet_index] = new_text.strip()
    entry["description"] = join_description_bullets(bullets)
    entries[entry_index] = entry
    updated[section] = entries
    return updated


def build_resume_context(parsed_structure: dict[str, Any] | None, raw_text: str | None = None) -> str:
    if not parsed_structure:
        return raw_text or ""
    content = {k: v for k, v in parsed_structure.items() if k != "_meta"}
    return json.dumps(content, default=str)

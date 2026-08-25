"""Normalize persisted resume content for PDF template rendering."""

from __future__ import annotations

import re
from typing import Any

_BULLET_PREFIXES = ("•", "-", "*", "–", "—")


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _split_description(description: str | None) -> list[str]:
    if not description:
        return []
    bullets: list[str] = []
    for raw_line in description.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        for prefix in _BULLET_PREFIXES:
            if line.startswith(prefix):
                line = line[len(prefix) :].strip()
                break
        if line:
            bullets.append(line)
    return bullets


def _normalize_entry(entry: dict[str, Any]) -> dict[str, Any] | None:
    title = _clean_text(entry.get("title"))
    organization = _clean_text(entry.get("organization"))
    date_range = _clean_text(entry.get("date_range"))
    description = _clean_text(entry.get("description"))
    bullets = _split_description(description)

    if not any([title, organization, date_range, bullets]):
        return None

    return {
        "title": title,
        "organization": organization,
        "date_range": date_range,
        "bullets": bullets,
    }


def _normalize_personal_info(info: dict[str, Any] | None) -> dict[str, Any] | None:
    if not info:
        return None

    name = _clean_text(info.get("name"))
    email = _clean_text(info.get("email"))
    phone = _clean_text(info.get("phone"))
    location = _clean_text(info.get("location"))

    contact_parts = [part for part in [email, phone, location] if part]
    contact_line = " | ".join(contact_parts) if contact_parts else None

    links: list[dict[str, str]] = []
    for link in info.get("detected_urls") or []:
        if isinstance(link, str) and link.strip():
            links.append({"label": link.strip(), "url": link.strip()})
        elif isinstance(link, dict):
            url = _clean_text(link.get("url"))
            if url:
                label = _clean_text(link.get("type")) or url
                links.append({"label": label, "url": url})

    if not any([name, contact_line, links]):
        return None

    return {
        "name": name or "Resume",
        "contact_line": contact_line,
        "links": links,
    }


def build_template_context(content: dict[str, Any]) -> dict[str, Any]:
    """Build a template-safe context with empty sections omitted."""
    personal = _normalize_personal_info(content.get("personal_information"))

    summary = _clean_text(content.get("professional_summary"))

    education = [
        entry
        for entry in (_normalize_entry(item) for item in content.get("education") or [])
        if entry
    ]

    experience = [
        entry
        for entry in (_normalize_entry(item) for item in content.get("experience") or [])
        if entry
    ]

    projects: list[dict[str, Any]] = []
    for item in content.get("projects") or []:
        title = _clean_text(item.get("title"))
        description = _clean_text(item.get("description"))
        bullets = _split_description(description)
        if title or bullets:
            projects.append({"title": title, "bullets": bullets})

    skills = [
        skill.strip()
        for skill in (content.get("skills") or [])
        if isinstance(skill, str) and skill.strip()
    ]

    certifications = [
        entry
        for entry in (_normalize_entry(item) for item in content.get("certifications") or [])
        if entry
    ]

    achievements = [
        item.strip()
        for item in (content.get("achievements") or [])
        if isinstance(item, str) and item.strip()
    ]

    links: list[dict[str, str]] = []
    for item in content.get("links") or []:
        if not isinstance(item, dict):
            continue
        url = _clean_text(item.get("url"))
        if url:
            label = _clean_text(item.get("type")) or url
            links.append({"label": label.title(), "url": url})

    return {
        "personal": personal,
        "summary": summary,
        "education": education,
        "experience": experience,
        "projects": projects,
        "skills": skills,
        "certifications": certifications,
        "achievements": achievements,
        "links": links,
    }


def sanitize_filename(label: str | None, *, fallback: str = "resume") -> str:
    """Create a filesystem-safe PDF filename stem."""
    base = (label or fallback).strip() or fallback
    safe = re.sub(r"[^\w\s-]", "", base, flags=re.UNICODE)
    safe = re.sub(r"[\s_-]+", "-", safe).strip("-").lower()
    return safe or fallback

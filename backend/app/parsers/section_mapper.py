"""Maps varied resume section headings to canonical section keys."""

from __future__ import annotations

import re

SECTION_ALIASES: dict[str, list[str]] = {
    "experience": [
        "work experience",
        "professional experience",
        "employment history",
        "career history",
        "relevant experience",
        "experience",
        "employment",
        "work history",
    ],
    "education": [
        "education",
        "academic background",
        "academic history",
        "educational background",
        "qualifications",
    ],
    "projects": [
        "projects",
        "personal projects",
        "key projects",
        "selected projects",
        "project experience",
    ],
    "skills": [
        "skills",
        "technical skills",
        "core competencies",
        "competencies",
        "technologies",
        "tools & technologies",
        "areas of expertise",
    ],
    "certifications": [
        "certifications",
        "certificates",
        "licenses",
        "licences",
        "professional certifications",
    ],
    "achievements": [
        "achievements",
        "awards",
        "honors",
        "honours",
        "accomplishments",
    ],
    "links": [
        "links",
        "profiles",
        "online profiles",
        "websites",
        "portfolio",
    ],
    "professional_summary": [
        "professional summary",
        "summary",
        "profile",
        "objective",
        "career objective",
        "about me",
        "overview",
        "executive summary",
    ],
    "personal_information": [
        "personal information",
        "contact",
        "contact information",
        "personal details",
    ],
}

def _normalize(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s&]", "", text.lower().strip())
    return re.sub(r"\s+", " ", cleaned)


_ALIAS_LOOKUP: dict[str, str] = {}
for canonical, aliases in SECTION_ALIASES.items():
    for alias in aliases:
        _ALIAS_LOOKUP[_normalize(alias)] = canonical


def match_section_heading(line: str) -> str | None:
    """Return canonical section key if line looks like a section heading."""
    normalized = _normalize(line)
    if not normalized or len(normalized) > 80:
        return None

    if normalized in _ALIAS_LOOKUP:
        return _ALIAS_LOOKUP[normalized]

    for alias, canonical in _ALIAS_LOOKUP.items():
        if normalized == alias or normalized.endswith(f" {alias}") or normalized.startswith(f"{alias} "):
            return canonical

    return None

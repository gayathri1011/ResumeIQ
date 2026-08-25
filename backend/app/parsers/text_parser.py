"""Shared text segmentation and section content parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.parsers.schema import CANONICAL_SECTIONS, ParsedResumeMeta, ParsedResumeStructure
from app.parsers.section_mapper import match_section_heading

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{3,4}")
URL_RE = re.compile(r"https?://\S+|www\.\S+|linkedin\.com/\S+|github\.com/\S+", re.IGNORECASE)
BULLET_RE = re.compile(r"^[\u2022\u2023\u25E6\u2043\u2219•\-\*]\s+")
DATE_RANGE_RE = re.compile(
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}"
    r"\s*(?:-|–|—|to)\s*"
    r"(?:present|current|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}|\d{4})",
    re.IGNORECASE,
)


@dataclass
class TextLine:
    text: str
    is_heading: bool = False
    font_size: float | None = None


@dataclass
class SectionBlock:
    key: str
    lines: list[str] = field(default_factory=list)


def normalize_lines(raw_text: str) -> list[str]:
    lines: list[str] = []
    for line in raw_text.splitlines():
        stripped = line.strip()
        if stripped:
            lines.append(stripped)
    return lines


def split_into_sections(lines: list[str], heading_flags: list[bool] | None = None) -> list[SectionBlock]:
    """Split lines into section blocks using heading detection."""
    if heading_flags is None:
        heading_flags = [False] * len(lines)

    blocks: list[SectionBlock] = []
    preamble: list[str] = []
    current_key: str | None = None
    current_lines: list[str] = []

    for idx, line in enumerate(lines):
        is_heading = heading_flags[idx] if idx < len(heading_flags) else False
        normalized_line = line.rstrip(":").strip()
        matched = match_section_heading(normalized_line)
        if matched and not (is_heading or _looks_like_heading(line) or len(normalized_line) < 50):
            matched = None

        if matched:
            if current_key is None and preamble:
                blocks.append(SectionBlock(key="personal_information", lines=preamble.copy()))
                preamble = []
            elif current_key:
                blocks.append(SectionBlock(key=current_key, lines=current_lines.copy()))
            current_key = matched
            current_lines = []
            continue

        if current_key is None:
            preamble.append(line)
        else:
            current_lines.append(line)

    if current_key:
        blocks.append(SectionBlock(key=current_key, lines=current_lines))
    elif preamble:
        blocks.append(SectionBlock(key="personal_information", lines=preamble))

    return blocks


def _looks_like_heading(line: str) -> bool:
    if match_section_heading(line):
        if line.isupper() and len(line) < 60:
            return True
        if line.endswith(":") and len(line) < 60:
            return True
        normalized = line.rstrip(":").strip()
        return match_section_heading(normalized) is not None
    return False


def parse_personal_information(lines: list[str]) -> dict[str, str | None]:
    text = "\n".join(lines)
    emails = EMAIL_RE.findall(text)
    phones = PHONE_RE.findall(text)
    urls = URL_RE.findall(text)

    name: str | None = None
    for line in lines[:3]:
        if EMAIL_RE.search(line) or URL_RE.search(line) or PHONE_RE.search(line):
            continue
        if 2 <= len(line.split()) <= 5 and len(line) < 60:
            name = line
            break

    result: dict[str, str | None] = {
        "name": name,
        "email": emails[0] if emails else None,
        "phone": phones[0] if phones else None,
        "location": None,
    }

    if not any(result.values()) and not urls:
        return {}

    links = [{"type": "url", "url": u} for u in urls]
    if links:
        result["detected_urls"] = ", ".join(urls)

    return {k: v for k, v in result.items() if v is not None}


def parse_bullet_items(lines: list[str]) -> list[str]:
    items: list[str] = []
    buffer: list[str] = []

    for line in lines:
        if BULLET_RE.match(line) or (line.startswith("- ") or line.startswith("* ")):
            if buffer:
                items.append(" ".join(buffer).strip())
                buffer = []
            items.append(BULLET_RE.sub("", line).removeprefix("- ").removeprefix("* ").strip())
        elif items and line and not DATE_RANGE_RE.search(line):
            items[-1] = f"{items[-1]} {line}".strip()
        else:
            if line:
                buffer.append(line)

    if buffer:
        items.append(" ".join(buffer).strip())

    return [item for item in items if item]


def parse_skills(lines: list[str]) -> list[str]:
    text = " ".join(lines)
    if not text.strip():
        return []

    # Split common delimiters used in resumes: commas, pipes, slashes, semicolons.
    if any(delimiter in text for delimiter in (",", "|", "/", ";")):
        parts = re.split(r"[,|/;]+", text)
        return [part.strip() for part in parts if part.strip()]

    bullets = parse_bullet_items(lines)
    if bullets:
        return bullets

    return [text.strip()] if text.strip() else []


def parse_entries(lines: list[str], entry_type: str) -> list[dict[str, str | None]]:
    """Parse multi-entry sections (experience, education, projects, certifications)."""
    entries: list[dict[str, str | None]] = []
    current: dict[str, str | None] = {}
    description_lines: list[str] = []

    def flush() -> None:
        nonlocal current, description_lines
        if current or description_lines:
            if description_lines:
                current["description"] = "\n".join(description_lines).strip() or None
            if any(v for v in current.values() if v):
                entries.append(current)
        current = {}
        description_lines = []

    for line in lines:
        date_match = DATE_RANGE_RE.search(line)
        is_bullet = bool(BULLET_RE.match(line) or line.startswith(("- ", "* ")))

        if date_match and not is_bullet:
            flush()
            title_part = DATE_RANGE_RE.sub("", line).strip(" -–—|,")
            current = {
                "title": title_part or None,
                "date_range": date_match.group(0).strip(),
                "organization": None,
                "description": None,
            }
        elif is_bullet:
            description_lines.append(
                BULLET_RE.sub("", line).removeprefix("- ").removeprefix("* ").strip()
            )
        elif not current and line:
            flush()
            current = {"title": line, "date_range": None, "organization": None, "description": None}
        elif current and line and not description_lines:
            if not current.get("organization"):
                current["organization"] = line
            else:
                description_lines.append(line)
        elif line:
            description_lines.append(line)

    flush()
    return entries


def build_structured_resume(blocks: list[SectionBlock]) -> ParsedResumeStructure:
    data: dict[str, object | None] = {key: None for key in CANONICAL_SECTIONS}
    found: list[str] = []

    for block in blocks:
        if not block.lines:
            continue

        key = block.key
        if key not in CANONICAL_SECTIONS:
            continue

        if key == "personal_information":
            parsed = parse_personal_information(block.lines)
            data[key] = parsed if parsed else None
        elif key == "professional_summary":
            text = "\n".join(block.lines).strip()
            data[key] = text if text else None
        elif key == "skills":
            skills = parse_skills(block.lines)
            data[key] = skills if skills else None
        elif key == "achievements":
            items = parse_bullet_items(block.lines)
            data[key] = items if items else None
        elif key == "links":
            links: list[dict[str, str]] = []
            for line in block.lines:
                for url in URL_RE.findall(line):
                    links.append({"type": "url", "url": url})
                if "linkedin" in line.lower():
                    links.append({"type": "linkedin", "url": line.strip()})
                elif "github" in line.lower():
                    links.append({"type": "github", "url": line.strip()})
            data[key] = links if links else None
        elif key in {"experience", "education", "projects", "certifications"}:
            entries = parse_entries(block.lines, key)
            data[key] = entries if entries else None

        if data.get(key) and key not in found:
            found.append(key)

    missing = [s for s in CANONICAL_SECTIONS if s not in found]
    structure = ParsedResumeStructure(
        personal_information=data["personal_information"],  # type: ignore[arg-type]
        professional_summary=data["professional_summary"],  # type: ignore[arg-type]
        education=data["education"],  # type: ignore[arg-type]
        experience=data["experience"],  # type: ignore[arg-type]
        projects=data["projects"],  # type: ignore[arg-type]
        skills=data["skills"],  # type: ignore[arg-type]
        certifications=data["certifications"],  # type: ignore[arg-type]
        achievements=data["achievements"],  # type: ignore[arg-type]
        links=data["links"],  # type: ignore[arg-type]
        meta=ParsedResumeMeta(sections_found=found, sections_missing=missing),
    )
    return structure

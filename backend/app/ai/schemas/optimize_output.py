"""Pydantic schemas and validation for AI resume optimization output."""

from __future__ import annotations

import copy
import json
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.ai.schemas.bullet_output import extract_quantifiers, find_fabricated_metrics
from app.parsers.schema import ParsedResumeStructure

STRUCTURAL_ENTRY_SECTIONS = ("experience", "education", "projects", "certifications")
STRUCTURAL_FIELDS = ("title", "organization", "date_range")


class OptimizationChangeOutput(BaseModel):
    section: str = Field(min_length=1)
    field_path: str | None = None
    before: str = ""
    after: str = ""
    why: str = Field(min_length=1)

    @field_validator("section", "why")
    @classmethod
    def strip_required(cls, value: str) -> str:
        return value.strip()

    @field_validator("before", "after", mode="before")
    @classmethod
    def coerce_text(cls, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            return ", ".join(str(item) for item in value if item is not None)
        if isinstance(value, dict):
            return json.dumps(value, default=str)
        return str(value)


class ResumeOptimizationAIOutput(BaseModel):
    optimized_content: dict[str, Any]
    changes: list[OptimizationChangeOutput] = Field(default_factory=list)


def normalize_token(value: str) -> str:
    return " ".join(value.lower().strip().split())


def normalize_skill(value: str) -> str:
    return normalize_token(value)


def collect_original_text_corpus(parsed: dict[str, Any]) -> str:
    parts: list[str] = []
    for key, value in parsed.items():
        if key == "_meta":
            continue
        parts.append(json.dumps(value, default=str))
    return " ".join(parts)


def validate_optimized_schema(optimized: dict[str, Any]) -> dict[str, Any]:
    """Validate optimized content against the canonical resume schema."""
    meta = optimized.get("_meta")
    model = ParsedResumeStructure.model_validate(optimized)
    result = model.to_storage_dict()
    if meta is not None:
        result["_meta"] = meta
    return result


def validate_structural_facts_preserved(
    original: dict[str, Any],
    optimized: dict[str, Any],
) -> list[str]:
    """Ensure employers, titles, dates, and skills are not invented or altered."""
    violations: list[str] = []

    for section in STRUCTURAL_ENTRY_SECTIONS:
        orig_entries = original.get(section) or []
        opt_entries = optimized.get(section) or []
        if len(orig_entries) != len(opt_entries):
            violations.append(f"{section} entry count changed")
            continue
        for index, (orig_entry, opt_entry) in enumerate(zip(orig_entries, opt_entries, strict=True)):
            if not isinstance(orig_entry, dict) or not isinstance(opt_entry, dict):
                continue
            for field in STRUCTURAL_FIELDS:
                orig_val = orig_entry.get(field)
                opt_val = opt_entry.get(field)
                if orig_val is None and opt_val is None:
                    continue
                if normalize_token(str(orig_val or "")) != normalize_token(str(opt_val or "")):
                    violations.append(
                        f"{section}[{index}].{field} changed from {orig_val!r} to {opt_val!r}"
                    )

    orig_skills = _dedupe_skills(_flatten_skills(original.get("skills")))
    opt_skills = _dedupe_skills(_flatten_skills(optimized.get("skills")))
    orig_set = {normalize_skill(skill) for skill in orig_skills}
    for skill in opt_skills:
        key = normalize_skill(skill)
        if key and key not in orig_set:
            violations.append(f"introduced skill not in original resume: {skill}")
    if orig_skills and not opt_skills:
        violations.append("skills section was removed")

    orig_personal = original.get("personal_information") or {}
    opt_personal = optimized.get("personal_information") or {}
    if isinstance(orig_personal, dict) and isinstance(opt_personal, dict):
        for field in ("name", "email", "phone", "location"):
            orig_val = orig_personal.get(field)
            opt_val = opt_personal.get(field)
            if orig_val and opt_val and normalize_token(str(orig_val)) != normalize_token(str(opt_val)):
                violations.append(f"personal_information.{field} was altered")

    return violations


def _split_skill_text(value: str) -> list[str]:
    """Split AI-joined skill strings into individual skills."""
    text = value.strip()
    if not text:
        return []
    # Models often return "Python | SQL | Excel" or "Python / SQL; Excel"
    parts = re.split(r"[|/;,\n]+", text)
    return [part.strip() for part in parts if part.strip()]


def _flatten_skills(skills_value: Any) -> list[str]:
    if skills_value is None:
        return []
    if isinstance(skills_value, list):
        flattened: list[str] = []
        for item in skills_value:
            if isinstance(item, str) and item.strip():
                flattened.extend(_split_skill_text(item))
            elif isinstance(item, dict):
                for value in item.values():
                    flattened.extend(_flatten_skills(value))
        return flattened
    if isinstance(skills_value, dict):
        flattened = []
        for value in skills_value.values():
            flattened.extend(_flatten_skills(value))
        return flattened
    if isinstance(skills_value, str) and skills_value.strip():
        return _split_skill_text(skills_value)
    return []


def _dedupe_skills(skills: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for skill in skills:
        key = normalize_skill(skill)
        if key and key not in seen:
            ordered.append(skill.strip())
            seen.add(key)
    return ordered


def _align_skills_to_original(original_skills: list[str], optimized_skills: Any) -> list[str]:
    """Keep only real original skills, prioritizing AI reorder when possible."""
    orig = _dedupe_skills(_flatten_skills(original_skills))
    if not orig:
        return _dedupe_skills(_flatten_skills(optimized_skills))

    orig_by_key = {normalize_skill(skill): skill for skill in orig}
    preferred: list[str] = []
    used: set[str] = set()
    for skill in _flatten_skills(optimized_skills):
        key = normalize_skill(skill)
        if key in orig_by_key and key not in used:
            preferred.append(orig_by_key[key])
            used.add(key)
    for skill in orig:
        key = normalize_skill(skill)
        if key not in used:
            preferred.append(skill)
            used.add(key)
    return preferred


def _is_hard_violation(violation: str) -> bool:
    lowered = violation.lower()
    return any(
        phrase in lowered
        for phrase in (
            "introduced metrics",
            "entry count",
            "skills section was removed",
            "skills were removed",
            "entries reduced",
            "was altered",
            "changed from",
        )
    )


def repair_optimized_content(
    original: dict[str, Any],
    optimized: dict[str, Any],
) -> dict[str, Any]:
    """Repair common AI formatting mistakes while preserving rewritten content."""
    result = copy.deepcopy(optimized)

    orig_skills = _flatten_skills(original.get("skills"))
    result["skills"] = _align_skills_to_original(orig_skills, result.get("skills"))

    for section in STRUCTURAL_ENTRY_SECTIONS:
        orig_entries = original.get(section) or []
        if not isinstance(orig_entries, list):
            continue
        opt_entries = result.get(section) or []
        if not isinstance(opt_entries, list):
            opt_entries = []
        if len(opt_entries) < len(orig_entries):
            opt_entries = list(opt_entries) + copy.deepcopy(orig_entries[len(opt_entries) :])
        for index, orig_entry in enumerate(orig_entries):
            if index >= len(opt_entries):
                break
            if not isinstance(orig_entry, dict):
                continue
            if not isinstance(opt_entries[index], dict):
                opt_entries[index] = copy.deepcopy(orig_entry)
                continue
            for field in STRUCTURAL_FIELDS:
                if orig_entry.get(field) is not None:
                    opt_entries[index][field] = orig_entry[field]
        result[section] = opt_entries

    for section in ("achievements",):
        orig_items = original.get(section) or []
        opt_items = result.get(section) or []
        if isinstance(orig_items, list) and isinstance(opt_items, list) and len(opt_items) < len(orig_items):
            result[section] = list(opt_items) + orig_items[len(opt_items) :]

    if original.get("personal_information"):
        result["personal_information"] = copy.deepcopy(original["personal_information"])

    if original.get("_meta"):
        result["_meta"] = copy.deepcopy(original["_meta"])

    return result


def validate_no_fabricated_content(
    original: dict[str, Any],
    optimized: dict[str, Any],
) -> list[str]:
    """Heuristic guard against invented metrics and untraceable numbers."""
    violations: list[str] = []
    corpus = collect_original_text_corpus(original)

    def check_text(field_path: str, before: str | None, after: str | None) -> None:
        if not after or before == after:
            return
        fabricated = find_fabricated_metrics(before or "", after, resume_context=corpus)
        if fabricated:
            violations.append(
                f"{field_path} introduced metrics not in original: {', '.join(sorted(fabricated))}"
            )

    if original.get("professional_summary") != optimized.get("professional_summary"):
        check_text(
            "professional_summary",
            str(original.get("professional_summary") or ""),
            str(optimized.get("professional_summary") or ""),
        )

    for section in ("experience", "projects"):
        for index, opt_entry in enumerate(optimized.get(section) or []):
            orig_entry = (original.get(section) or [])[index] if index < len(original.get(section) or []) else {}
            if not isinstance(opt_entry, dict):
                continue
            check_text(
                f"{section}[{index}].description",
                str((orig_entry or {}).get("description") or ""),
                str(opt_entry.get("description") or ""),
            )

    return violations


def section_changed(original: dict[str, Any], optimized: dict[str, Any], section: str) -> bool:
    return json.dumps(original.get(section), sort_keys=True, default=str) != json.dumps(
        optimized.get(section), sort_keys=True, default=str
    )


def snippet(value: Any, *, max_len: int = 240) -> str:
    text = str(value or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def reconcile_changes(
    original: dict[str, Any],
    optimized: dict[str, Any],
    ai_changes: list[OptimizationChangeOutput],
    *,
    target_role: str,
) -> list[dict[str, Any]]:
    """Ensure each changed section has a grounded change record with a why explanation."""
    tracked_sections = [
        "professional_summary",
        "skills",
        "experience",
        "projects",
        "achievements",
    ]
    changes_by_section: dict[str, list[OptimizationChangeOutput]] = {}
    for change in ai_changes:
        changes_by_section.setdefault(change.section, []).append(change)

    reconciled: list[dict[str, Any]] = []
    for section in tracked_sections:
        if not section_changed(original, optimized, section):
            continue

        section_changes = changes_by_section.get(section, [])
        if section_changes:
            for change in section_changes:
                item = change.model_dump()
                item["change_id"] = item.get("field_path") or item.get("section") or section
                reconciled.append(item)
            continue

        before_val = original.get(section)
        after_val = optimized.get(section)
        reconciled.append(
            {
                "change_id": section,
                "section": section,
                "field_path": section,
                "before": snippet(before_val),
                "after": snippet(after_val),
                "why": (
                    f"Updated {section.replace('_', ' ')} to better align with "
                    f"{target_role}, using only existing resume content."
                ),
            }
        )

    return reconciled


def validate_change_explanations(
    original: dict[str, Any],
    optimized: dict[str, Any],
    changes: list[dict[str, Any]],
) -> list[str]:
    violations: list[str] = []
    changed_sections = {
        section
        for section in (
            "professional_summary",
            "skills",
            "experience",
            "projects",
            "achievements",
        )
        if section_changed(original, optimized, section)
    }

    explained_sections = {change["section"] for change in changes if change.get("why", "").strip()}
    missing = changed_sections - explained_sections
    if missing:
        violations.append(f"missing explanations for changed sections: {', '.join(sorted(missing))}")

    for change in changes:
        if not change.get("why", "").strip():
            violations.append(f"empty why for section {change.get('section')}")

    untouched_with_changes = {
        change["section"]
        for change in changes
        if change.get("section") and not section_changed(original, optimized, change["section"])
    }
    if untouched_with_changes:
        violations.append(
            "changes listed for untouched sections: " + ", ".join(sorted(untouched_with_changes))
        )

    return violations

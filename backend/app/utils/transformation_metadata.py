"""Helpers for building role-version transformation metadata."""

from __future__ import annotations

import re
from typing import Any


SECTION_LABELS = {
    "professional_summary": "Summary",
    "skills": "Skills",
    "experience": "Experience",
    "projects": "Projects",
    "achievements": "Achievements",
    "education": "Education",
    "certifications": "Certifications",
}


def build_transformation_insights(
    changes: list[dict[str, Any]],
    *,
    target_role: str,
    original: dict[str, Any],
) -> dict[str, Any]:
    sections = []
    for change in changes:
        section = change.get("section") or ""
        if not section:
            continue
        sections.append(
            {
                "section": section,
                "headline": SECTION_LABELS.get(section, section.replace("_", " ").title()),
                "explanation": change.get("why")
                or f"Updated for {target_role} relevance.",
            }
        )

    skills = original.get("skills") or []
    top_strengths = [str(skill) for skill in skills[:5] if str(skill).strip()]

    improvements: list[str] = []
    if not original.get("achievements"):
        improvements.append("Add measurable achievements where possible.")
    if len(skills) < 5:
        improvements.append("Expand the skills section with tools you genuinely know.")
    if not improvements:
        improvements.append("Strengthen project descriptions with clearer outcomes.")

    return {
        "summary": f"Tailored your resume for the {target_role} role while preserving factual accuracy.",
        "sections": sections,
        "top_strengths": top_strengths,
        "recommended_improvements": improvements[:3],
    }


def _extract_jd_terms(job_description_text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+#./-]{1,}", job_description_text)
    stopwords = {
        "and",
        "the",
        "with",
        "for",
        "you",
        "will",
        "our",
        "your",
        "that",
        "this",
        "from",
        "have",
        "are",
        "job",
        "role",
        "work",
        "team",
        "using",
    }
    terms: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        normalized = token.lower()
        if len(normalized) < 3 or normalized in stopwords:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        terms.append(token)
    return terms[:40]


def build_job_match_details(
    original: dict[str, Any],
    job_description_text: str | None,
    *,
    target_role: str,
) -> dict[str, Any]:
    if not job_description_text:
        return {
            "match_score": None,
            "matched_requirements": [],
            "missing_requirements": [],
            "explanation": "",
        }

    resume_skills = [str(skill).strip() for skill in (original.get("skills") or []) if str(skill).strip()]
    jd_lower = job_description_text.lower()
    matched = [skill for skill in resume_skills if skill.lower() in jd_lower]

    resume_blob = " ".join(
        [
            jd_lower,
            " ".join(skill.lower() for skill in resume_skills),
            str(original.get("professional_summary") or "").lower(),
        ]
    )
    missing: list[str] = []
    for term in _extract_jd_terms(job_description_text):
        if term.lower() in resume_blob:
            continue
        if any(term.lower() in skill.lower() or skill.lower() in term.lower() for skill in resume_skills):
            continue
        missing.append(term)
        if len(missing) >= 8:
            break

    total = len(matched) + len(missing)
    match_score = round((len(matched) / total) * 100) if total else 75
    explanation = (
        f"Compared your master resume against the provided job description for {target_role}. "
        "Missing items are mentioned in the JD but not strongly represented in your resume."
    )
    if missing:
        explanation += (
            f" Consider highlighting {missing[0]} only if you have relevant experience."
        )

    return {
        "match_score": match_score,
        "matched_requirements": matched[:10],
        "missing_requirements": missing,
        "explanation": explanation,
    }


def estimate_transformation_scores(
    changes: list[dict[str, Any]],
    job_match_details: dict[str, Any],
) -> dict[str, int]:
    change_boost = min(20, len(changes) * 3)
    role_relevance_score = min(96, 72 + change_boost)
    ats_score = min(94, 70 + change_boost)
    job_match_score = job_match_details.get("match_score")
    if job_match_score is None:
        job_match_score = min(90, 68 + change_boost)
    return {
        "role_relevance_score": role_relevance_score,
        "ats_score": ats_score,
        "job_match_score": job_match_score,
    }

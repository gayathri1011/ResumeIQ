"""Mock AI provider for tests and local development without API keys."""

from __future__ import annotations

import json
from typing import Any

from app.ai.providers.types import CompletionResult
from app.ai.schemas.analysis_output import DIMENSION_KEYS, ResumeAnalysisOutput


def _is_job_match_prompt(messages: list[dict[str, str]] | None) -> bool:
    if not messages:
        return False
    combined = " ".join(message.get("content", "") for message in messages).lower()
    return "job match analysis" in combined or "compare this resume to the job" in combined


def _build_valid_match_output(messages: list[dict[str, str]] | None = None) -> dict[str, object]:
    user_text = ""
    if messages:
        user_text = messages[-1].get("content", "")

    low_score = "unrelated" in user_text.lower() or '"skills": []' in user_text
    skills_score = 20 if low_score else 78

    return {
        "breakdown": {
            "skills_match": skills_score,
            "experience_match": 25 if low_score else 72,
            "keyword_match": 15 if low_score else 65,
            "project_relevance": 20 if low_score else 70,
            "education_match": 30 if low_score else 80,
        },
        "matched_skills": [] if low_score else ["Python", "SQL"],
        "missing_skills": ["AWS", "Kubernetes"] if not low_score else ["Python", "SQL", "AWS"],
        "missing_keywords": ["microservices", "CI/CD"] if not low_score else ["agile", "backend"],
        "explanations": [
            {"category": "skills_match", "summary": "Limited overlap between resume skills and JD requirements." if low_score else "Python and SQL appear in both resume and JD."},
            {"category": "experience_match", "summary": "Resume experience does not align with JD requirements." if low_score else "Experience aligns with backend responsibilities."},
            {"category": "keyword_match", "summary": "Few JD keywords reflected in resume." if low_score else "Several JD keywords are present."},
            {"category": "project_relevance", "summary": "Projects are not relevant to the role." if low_score else "Projects demonstrate relevant technologies."},
            {"category": "education_match", "summary": "Education requirements not met." if low_score else "Education aligns with JD requirements."},
        ],
        "summary": "Low match — resume lacks most required skills." if low_score else "Moderate-to-strong match on core skills with some gaps.",
    }


def _is_skill_gap_prompt(messages: list[dict[str, str]] | None) -> bool:
    if not messages:
        return False
    combined = " ".join(message.get("content", "") for message in messages).lower()
    return "skill gap advisor" in combined or "skill gap explanations" in combined


def _build_valid_skill_gap_output(messages: list[dict[str, str]] | None = None) -> dict[str, object]:
    missing = ["AWS", "Kubernetes"]
    if messages:
        content = messages[-1].get("content", "")
        if '"skill": "Python"' in content and '"priority": "high"' in content:
            missing = ["Python"]

    return {
        "missing_skill_explanations": [
            {
                "skill": skill,
                "why_it_matters": f"The JD references {skill} in requirements or responsibilities.",
            }
            for skill in missing
        ],
        "learning_roadmap": [
            {"skill": missing[0], "rationale": "Foundational skill to address first based on JD emphasis."},
            *[
                {"skill": skill, "rationale": f"Build on prior skills before focusing on {skill}."}
                for skill in missing[1:]
            ],
        ],
    }


def _is_job_extraction_prompt(messages: list[dict[str, str]] | None) -> bool:
    if not messages:
        return False
    combined = " ".join(message.get("content", "") for message in messages).lower()
    return "job description extraction" in combined or "extract structured requirements" in combined


def _build_valid_job_output(messages: list[dict[str, str]] | None = None) -> dict[str, object]:
    user_text = ""
    if messages:
        user_text = messages[-1].get("content", "")

    title = "Software Engineer"
    if "senior" in user_text.lower():
        title = "Senior Software Engineer"

    return {
        "job_title": title,
        "required_skills": ["Python", "SQL", "REST APIs"],
        "preferred_skills": ["AWS", "Docker"],
        "experience_requirements": {
            "years_min": 3,
            "years_max": None,
            "seniority_level": "Senior" if "senior" in user_text.lower() else None,
            "description": "3+ years of professional software development experience.",
        },
        "education_requirements": ["Bachelor's degree in Computer Science or related field"],
        "tools": ["Git", "Jira"],
        "technologies": ["Python", "PostgreSQL", "FastAPI"],
        "responsibilities": [
            "Design and build backend services.",
            "Collaborate with product and design teams.",
        ],
        "keywords": ["microservices", "agile", "CI/CD"],
    }


def _is_resume_optimize_prompt(messages: list[dict[str, str]] | None) -> bool:
    if not messages:
        return False
    combined = " ".join(message.get("content", "") for message in messages).lower()
    return "resume optimizer" in combined or "optimize this resume" in combined


def _extract_resume_json(user_text: str) -> dict[str, Any]:
    marker = "ORIGINAL RESUME (structured JSON"
    if marker not in user_text:
        return {}
    section = user_text.split(marker, 1)[1]
    section = section.split(":", 1)[1] if ":" in section else section
    for stop in ("Optimize these areas", "Return JSON"):
        if stop in section:
            section = section.split(stop, 1)[0]
    section = section.strip()
    try:
        return json.loads(section)
    except json.JSONDecodeError:
        return {}


def _build_valid_resume_optimize_output(messages: list[dict[str, str]] | None = None) -> dict[str, object]:
    user_text = ""
    if messages:
        user_text = messages[-1].get("content", "")

    original = _extract_resume_json(user_text)
    if not original:
        original = {
            "skills": ["Python", "SQL"],
            "experience": [
                {
                    "title": "Engineer",
                    "organization": "Acme",
                    "date_range": "2020 - Present",
                    "description": "Worked on backend APIs.",
                }
            ],
        }

    optimized = json.loads(json.dumps(original))
    changes: list[dict[str, str]] = []

    if "FABRICATE_METRIC_TEST" in user_text:
        if optimized.get("experience"):
            optimized["experience"][0]["description"] = (
                "Built backend services with Python, improving throughput by 40%."
            )
        return {
            "optimized_content": optimized,
            "changes": [
                {
                    "section": "experience",
                    "field_path": "experience[0].description",
                    "before": str(original.get("experience", [{}])[0].get("description", "")),
                    "after": optimized["experience"][0]["description"],
                    "why": "Added fabricated metric for testing.",
                }
            ],
        }

    target_role = "Software Engineer"
    if "TARGET ROLE:" in user_text:
        role_section = user_text.split("TARGET ROLE:", 1)[1]
        target_role = role_section.split("\n", 1)[0].strip() or target_role

    if optimized.get("skills"):
        before_skills = list(optimized["skills"])
        optimized["skills"] = sorted(
            optimized["skills"],
            key=lambda skill: 0 if "python" in skill.lower() else 1,
        )
        if before_skills != optimized["skills"]:
            changes.append(
                {
                    "change_id": "skills",
                    "section": "skills",
                    "field_path": "skills",
                    "before": ", ".join(before_skills),
                    "after": ", ".join(optimized["skills"]),
                    "why": (
                        f"Reordered skills to surface Python and backend-relevant items first "
                        f"for {target_role}."
                    ),
                }
            )

    if optimized.get("experience"):
        entry = optimized["experience"][0]
        before_desc = str(entry.get("description") or "")
        entry["description"] = (
            "Designed and delivered backend services with Python and PostgreSQL, "
            "emphasizing API reliability for production systems."
        )
        if before_desc != entry["description"]:
            changes.append(
                {
                    "change_id": "experience[0].description",
                    "section": "experience",
                    "field_path": "experience[0].description",
                    "before": before_desc,
                    "after": entry["description"],
                    "why": (
                        "Strengthened action verbs and highlighted Python/PostgreSQL work "
                        f"relevant to {target_role} without changing employers or dates."
                    ),
                }
            )

    if optimized.get("projects"):
        project = optimized["projects"][0]
        before_desc = str(project.get("description") or "")
        project["description"] = (
            "Built FastAPI microservices demonstrating backend API design and service ownership."
        )
        if before_desc != project["description"]:
            changes.append(
                {
                    "change_id": "projects[0].description",
                    "section": "projects",
                    "field_path": "projects[0].description",
                    "before": before_desc,
                    "after": project["description"],
                    "why": (
                        "Clarified project impact and backend relevance for the target role."
                    ),
                }
            )

    if optimized.get("professional_summary"):
        before_summary = optimized["professional_summary"]
        optimized["professional_summary"] = (
            f"Backend-focused engineer with experience building APIs and services aligned with {target_role}."
        )
        changes.append(
            {
                "change_id": "professional_summary",
                "section": "professional_summary",
                "field_path": "professional_summary",
                "before": before_summary,
                "after": optimized["professional_summary"],
                "why": f"Rewrote summary to emphasize backend strengths for {target_role}.",
            }
        )

    return {"optimized_content": optimized, "changes": changes}


def _is_bullet_improve_prompt(messages: list[dict[str, str]] | None) -> bool:
    if not messages:
        return False
    combined = " ".join(message.get("content", "") for message in messages).lower()
    return "resume bullet improver" in combined or "improve this resume bullet" in combined


def _extract_original_bullet(user_text: str) -> str:
    marker = "ORIGINAL BULLET:"
    if marker not in user_text:
        return user_text
    section = user_text.split(marker, 1)[1]
    for stop in ("RESUME CONTEXT", "TARGET ROLE", "REGENERATE MODE"):
        if stop in section:
            section = section.split(stop, 1)[0]
    return section.strip()


def _build_valid_bullet_output(messages: list[dict[str, str]] | None = None) -> dict[str, object]:
    user_text = ""
    if messages:
        user_text = messages[-1].get("content", "")

    if "FABRICATE_METRIC_TEST" in user_text:
        return {
            "improved_text": "Improved API performance by 40% through backend optimization.",
            "changes_summary": "Added fabricated metric for testing.",
            "metric_placeholder_used": False,
            "suggested_metric_prompt": None,
        }

    original = _extract_original_bullet(user_text)
    regenerate = "regenerate mode: true" in user_text.lower()
    has_metrics = any(char.isdigit() for char in original)

    if regenerate:
        improved_text = (
            "Owned backend API development end-to-end, partnering with product "
            "to deliver reliable services."
        )
        changes_summary = "Varied structure and emphasized ownership for a fresh rewrite."
    elif has_metrics:
        improved_text = (
            "Designed and maintained backend APIs, preserving the original scope "
            "and measurable outcomes."
        )
        changes_summary = "Strengthened the action verb and clarified delivery scope."
    else:
        improved_text = (
            "Designed and maintained backend APIs with clear ownership of implementation "
            "[add measurable outcome, e.g. % improvement or team size]."
        )
        changes_summary = (
            "Strengthened the action verb and clarified scope without inventing metrics."
        )

    return {
        "improved_text": improved_text,
        "changes_summary": changes_summary,
        "metric_placeholder_used": not has_metrics,
        "suggested_metric_prompt": (
            "Add a real metric such as request volume, latency improvement, or team size."
            if not has_metrics
            else None
        ),
    }


def _resolve_mock_output(messages: list[dict[str, str]] | None) -> dict[str, object]:
    if _is_resume_optimize_prompt(messages):
        return _build_valid_resume_optimize_output(messages)
    if _is_bullet_improve_prompt(messages):
        return _build_valid_bullet_output(messages)
    if _is_skill_gap_prompt(messages):
        return _build_valid_skill_gap_output(messages)
    if _is_job_match_prompt(messages):
        return _build_valid_match_output(messages)
    if _is_job_extraction_prompt(messages):
        return _build_valid_job_output(messages)
    return _build_valid_output(messages)


class MockAIProvider:
    """Deterministic mock — returns valid analysis JSON."""

    def __init__(self, *, malformed_first: bool = False, invalid_json: bool = False) -> None:
        self._malformed_first = malformed_first
        self._invalid_json = invalid_json
        self._call_count = 0

    async def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> CompletionResult:
        self._call_count += 1

        if self._invalid_json and self._call_count == 1:
            return CompletionResult(
                content="{ not valid json",
                model_used="mock-model",
                token_usage={"input": 10, "output": 5, "total": 15},
            )

        if self._malformed_first and self._call_count == 1:
            bad = _resolve_mock_output(messages)
            if _is_resume_optimize_prompt(messages):
                bad["optimized_content"] = {}
            elif _is_bullet_improve_prompt(messages):
                bad["improved_text"] = ""
            elif _is_skill_gap_prompt(messages):
                bad["missing_skill_explanations"] = "not-a-list"
            elif _is_job_match_prompt(messages):
                bad["breakdown"] = {"skills_match": "bad"}
            elif _is_job_extraction_prompt(messages):
                bad["required_skills"] = "not-a-list"
            else:
                bad["dimensions"] = bad["dimensions"][:5]  # too few dimensions
            return CompletionResult(
                content=json.dumps(bad),
                model_used="mock-model",
                token_usage={"input": 100, "output": 200, "total": 300},
            )

        output = _resolve_mock_output(messages)
        return CompletionResult(
            content=json.dumps(output),
            model_used="mock-model",
            token_usage={"input": 100, "output": 200, "total": 300},
        )

    async def embed(self, text: str) -> list[float]:
        from app.core.config import settings

        return [0.1] * settings.embedding_dimensions

    @property
    def call_count(self) -> int:
        return self._call_count


def _build_valid_output(messages: list[dict[str, str]] | None = None) -> dict[str, object]:
    user_text = ""
    if messages:
        user_text = messages[-1].get("content", "")

    missing_certs = "certifications" in user_text and "SECTIONS MISSING" in user_text

    dimensions = []
    for key in DIMENSION_KEYS:
        explanation = f"Assessment for {key} based on provided resume content."
        disclaimer = None
        score = 72

        if key == "certifications" and missing_certs:
            score = 15
            explanation = (
                "No certifications section was found in the parsed resume structure. "
                "Cannot score certifications that are not present."
            )
        if key == "ats_compatibility":
            disclaimer = (
                "Estimated ATS compatibility score based on implemented checks only — "
                "not a guarantee of performance in any real ATS system."
            )

        dimensions.append(
            {"key": key, "score": score, "explanation": explanation, "disclaimer": disclaimer}
        )

    return {
        "overall_score": 68,
        "summary": "Resume contains experience and skills sections with identifiable content.",
        "dimensions": dimensions,
        "issues": [
            {
                "severity": "medium",
                "category": "certifications" if missing_certs else "content_quality",
                "title": "Missing certifications section" if missing_certs else "Limited quantified metrics",
                "description": (
                    "The certifications section is absent from the parsed resume."
                    if missing_certs
                    else "Few bullets include measurable outcomes."
                ),
                "suggested_fix": None if missing_certs else "Add metrics where they exist in the resume.",
                "grounded_in_resume": True,
            }
        ],
    }

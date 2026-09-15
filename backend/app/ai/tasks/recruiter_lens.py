"""Evidence-grounded recruiter scan analysis with deterministic visibility scores."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.ai.client import AIService
from app.ai.prompts.loader import load_prompt
from app.ai.schemas.recruiter_lens_output import RecruiterLensOutput
from app.ai.utils import hash_resume_content
from app.core.database import MongoSession
from app.core.exceptions import AppError
from app.models.enums import AIResultType, AIServiceName
from app.repositories import AIAnalysisResultRepository, ResumeRepository, ResumeVersionRepository
from app.utils.version_content import get_version_content, resolve_version

PROMPT_FILE = "recruiter_lens_v1.yaml"
PROMPT_VERSION = "recruiter_lens_v1"


class RecruiterLensAnalyzer:
    def __init__(self, ai_service: AIService, session: MongoSession) -> None:
        self.ai_service = ai_service
        self.session = session
        self.resume_repo = ResumeRepository(session)
        self.version_repo = ResumeVersionRepository(session)
        self.ai_result_repo = AIAnalysisResultRepository(session)

    async def analyze(self, resume_id: UUID, *, resume_version_id: UUID | None = None) -> dict[str, Any]:
        resume = await self.resume_repo.get_by_id(resume_id)
        if resume is None:
            raise AppError("Resume not found.", code="resume_not_found", status_code=404)

        version = await resolve_version(
            self.version_repo, resume_id, version_id=resume_version_id, required=False
        )
        parsed = get_version_content(version) if version else resume.parsed_structure
        raw_text = (version.raw_text if version else resume.raw_text) or ""
        if not parsed:
            raise AppError("Resume has not been parsed yet.", code="resume_not_parsed", status_code=422)

        input_hash = f"{hash_resume_content(parsed)}:{PROMPT_VERSION}"
        cached = await self.ai_result_repo.get_by_input_hash_and_service(
            input_hash, AIServiceName.RECRUITER_LENS
        )
        version_id = version.id if version else None
        if cached:
            return self._build_response(cached, resume_id, version_id, cached=True)

        prompt_data = load_prompt(PROMPT_FILE)
        user_prompt = prompt_data["user_template"].format(
            resume_json=json.dumps(parsed, indent=2, default=str),
            raw_text=raw_text[:8000],
        )
        output, completion = await self.ai_service.complete_structured(
            prompt=user_prompt,
            system_prompt=prompt_data["system"],
            output_schema=RecruiterLensOutput,
            prompt_version=PROMPT_VERSION,
        )
        payload = self._build_payload(output, parsed)
        result = await self.ai_result_repo.create(
            service_name=AIServiceName.RECRUITER_LENS,
            input_hash=input_hash,
            result_type=AIResultType.RECRUITER_LENS,
            payload=payload,
            model_used=completion.model_used,
            prompt_version=PROMPT_VERSION,
            token_usage=completion.token_usage,
            resume_id=resume_id,
            resume_version_id=version_id,
        )
        return self._build_response(result, resume_id, version_id, cached=False)

    def _build_payload(self, output: RecruiterLensOutput, parsed: dict[str, Any]) -> dict[str, Any]:
        scores = self._scores(parsed)
        attention = self._attention_map(parsed)
        return {
            "recruiter_snapshot": output.recruiter_snapshot.model_dump(),
            "first_impression": output.first_impression,
            "clarity": output.clarity,
            "scores": scores,
            "attention_map": attention,
            "visible_strengths": [item.model_dump() for item in output.visible_strengths],
            "potentially_missed": [item.model_dump() for item in output.potentially_missed],
            "risks": [item.model_dump() for item in output.risks],
            "improvements": [item.model_dump() for item in output.improvements],
            "current_positioning": output.current_positioning,
            "recommended_positioning": output.recommended_positioning,
            "limitations": output.limitations,
            "analyzed_at": datetime.now(UTC),
        }

    def _scores(self, parsed: dict[str, Any]) -> list[dict[str, Any]]:
        summary = str(parsed.get("professional_summary") or "")
        experience = parsed.get("experience") or []
        projects = parsed.get("projects") or []
        skills = self._strings(parsed.get("skills"))
        achievements = self._strings(parsed.get("achievements"))
        corpus = json.dumps(parsed, default=str)
        metric_count = len(re.findall(r"(?:\b\d+(?:\.\d+)?%|\b\d+[+]?(?:\s*years?)?|\$\s?\d+|\b\d+[kKmMbB]\b)", corpus))
        role_titles = [str(item.get("title") or "") for item in experience if isinstance(item, dict)]
        has_role_signal = bool(summary.strip() or role_titles)
        role_clarity = min(100, 35 + (25 if summary.strip() else 0) + (25 if role_titles else 0) + (15 if len(role_titles) == 1 else 5 if role_titles else 0))
        technical_visibility = min(100, 30 + min(40, len(skills) * 8) + (20 if projects else 0) + (10 if self._technical_terms(skills) else 0))
        impact_visibility = min(100, 20 + min(50, metric_count * 15) + (20 if achievements else 0) + (10 if any(self._has_action_result(str(item)) for item in experience + projects) else 0))
        direction_terms = self._direction_terms(role_titles, summary)
        career_direction = min(100, 30 + min(40, len(direction_terms) * 15) + (20 if len(role_titles) <= 2 and role_titles else 0) + (10 if projects else 0))
        differentiation = min(100, 25 + (25 if projects else 0) + (20 if achievements else 0) + (15 if len(skills) >= 5 else 0) + (15 if metric_count else 0))
        return [
            self._score("role_clarity", "Role clarity", role_clarity, "A clear role signal comes from the professional summary and most recent experience title." if has_role_signal else "No clear headline, summary, or experience title was found in the parsed resume."),
            self._score("technical_visibility", "Technical visibility", technical_visibility, f"The resume lists {len(skills)} skill{'s' if len(skills) != 1 else ''} and {len(projects)} project{'s' if len(projects) != 1 else ''} that a quick scan can surface."),
            self._score("impact_visibility", "Impact visibility", impact_visibility, f"The parsed resume contains {metric_count} measurable signal{'s' if metric_count != 1 else ''} and {len(achievements)} achievement entr{'y' if len(achievements) == 1 else 'ies'} that can show outcomes."),
            self._score("career_direction", "Career direction", career_direction, "Direction is estimated from repeated role language, the summary, skills, and projects."),
            self._score("differentiation", "Differentiation", differentiation, "Differentiation is based on specific projects, achievements, technical breadth, and measurable evidence present in the resume."),
        ]

    def _attention_map(self, parsed: dict[str, Any]) -> list[dict[str, Any]]:
        sections = [
            ("Current role", bool(parsed.get("experience")), 92),
            ("Recent experience", bool(parsed.get("experience")), 86),
            ("Technical skills", bool(parsed.get("skills")), 78),
            ("Projects", bool(parsed.get("projects")), 68),
            ("Education", bool(parsed.get("education")), 48),
        ]
        visible = [item for item in sections if item[1]]
        if not visible:
            visible = [("Resume structure", True, 25)]
        return [{"area": area, "visibility": value, "rationale": "Estimated from section presence and the amount of scannable content; this is not eye-tracking data."} for area, _, value in visible]

    def _score(self, key: str, label: str, score: int, explanation: str) -> dict[str, Any]:
        return {"key": key, "label": label, "score": max(0, min(100, score)), "explanation": explanation}

    def _strings(self, value: Any) -> list[str]:
        return [str(item).strip() for item in (value or []) if str(item).strip()]

    def _technical_terms(self, skills: list[str]) -> list[str]:
        return [skill for skill in skills if any(char.isupper() for char in skill) or any(token in skill.lower() for token in ("api", "sql", "cloud", "data", "python", "javascript"))]

    def _has_action_result(self, value: str) -> bool:
        return bool(re.search(r"\b(built|led|improved|reduced|increased|delivered|launched|created)\b", value.lower()))

    def _direction_terms(self, titles: list[str], summary: str) -> set[str]:
        stop = {"the", "and", "for", "with", "senior", "junior", "engineer", "developer"}
        return {token for token in re.findall(r"[a-zA-Z]{4,}", " ".join(titles) + " " + summary.lower()) if token not in stop}

    def _build_response(self, result: Any, resume_id: UUID, version_id: UUID | None, *, cached: bool) -> dict[str, Any]:
        return {
            "lens_id": result.id,
            "resume_id": resume_id,
            "resume_version_id": version_id,
            "cached": cached,
            **result.payload,
            "prompt_version": result.prompt_version or PROMPT_VERSION,
        }

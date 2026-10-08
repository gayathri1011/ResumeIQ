"""Candidate Profile Builder service.

Assembles a compact, sanitized profile representation from EXISTING stored records
(Resume, ResumeVersion, ResumeAnalysis, JobMatch, CareerTrajectory, RecruiterLens,
and completed InterviewSessions) without triggering expensive AI re-analyses.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.core.database import MongoSession
from app.models.enums import AIServiceName, AnalysisStatus, InterviewStatus
from app.models.resume import Resume
from app.repositories import (
    AIAnalysisResultRepository,
    InterviewSessionRepository,
    JobDescriptionRepository,
    JobMatchRepository,
    ResumeAnalysisRepository,
    ResumeRepository,
    ResumeVersionRepository,
)
from app.utils.version_content import get_version_content, resolve_version


@dataclass
class CompactProfile:
    headline: str = "Candidate"
    skills: list[str] = field(default_factory=list)
    experience_highlights: list[dict[str, str]] = field(default_factory=list)
    project_highlights: list[dict[str, str]] = field(default_factory=list)
    education: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    resume_score: int | None = None
    trajectory_target_roles: list[str] = field(default_factory=list)
    recruiter_visible_strengths: list[str] = field(default_factory=list)
    job_matched_skills: list[str] = field(default_factory=list)
    job_missing_skills: list[str] = field(default_factory=list)
    interview_verified_skills: list[dict[str, Any]] = field(default_factory=list)

    def to_compact_text(self, max_chars: int = 3000) -> str:
        """Format the profile into a clean, compact text block for prompt injection."""
        sections: list[str] = []

        sections.append(f"CURRENT PROFILE: {self.headline}")
        if self.resume_score is not None:
            sections.append(f"RESUME QUALITY SCORE: {self.resume_score}/100")

        if self.skills:
            sections.append("CORE SKILLS: " + ", ".join(self.skills[:20]))

        if self.experience_highlights:
            exp_lines = []
            for item in self.experience_highlights[:3]:
                title = item.get("title", "")
                org = item.get("organization", "")
                desc = item.get("description", "")
                exp_lines.append(f"• {title} at {org}: {desc[:120]}")
            sections.append("RECENT EXPERIENCE:\n" + "\n".join(exp_lines))

        if self.project_highlights:
            proj_lines = []
            for item in self.project_highlights[:2]:
                title = item.get("title", "")
                desc = item.get("description", "")
                proj_lines.append(f"• {title}: {desc[:100]}")
            sections.append("KEY PROJECTS:\n" + "\n".join(proj_lines))

        if self.education:
            sections.append("EDUCATION: " + "; ".join(self.education[:2]))

        if self.certifications:
            sections.append("CERTIFICATIONS: " + "; ".join(self.certifications[:3]))

        if self.trajectory_target_roles:
            sections.append("IDENTIFIED CAREER PATHS: " + ", ".join(self.trajectory_target_roles[:3]))

        if self.recruiter_visible_strengths:
            sections.append("PROMINENT RECRUITER SIGNALS: " + "; ".join(self.recruiter_visible_strengths[:3]))

        if self.job_missing_skills:
            sections.append("KNOWN JOB SKILL GAPS: " + ", ".join(self.job_missing_skills[:10]))

        if self.interview_verified_skills:
            iv_lines = [
                f"{item.get('skill')}: {item.get('score')}%"
                for item in self.interview_verified_skills[:5]
            ]
            sections.append("VERIFIED INTERVIEW COMPETENCIES: " + ", ".join(iv_lines))

        full_text = "\n\n".join(sections)
        if len(full_text) > max_chars:
            return full_text[:max_chars] + "... [truncated]"
        return full_text


class CandidateProfileBuilder:
    def __init__(self, session: MongoSession) -> None:
        self.session = session
        self.resume_repo = ResumeRepository(session)
        self.version_repo = ResumeVersionRepository(session)
        self.analysis_repo = ResumeAnalysisRepository(session)
        self.ai_result_repo = AIAnalysisResultRepository(session)
        self.match_repo = JobMatchRepository(session)
        self.job_repo = JobDescriptionRepository(session)
        self.interview_repo = InterviewSessionRepository(session)

    async def build_profile(
        self,
        resume_id: UUID,
        *,
        resume_version_id: UUID | None = None,
        job_description_id: UUID | None = None,
    ) -> CompactProfile:
        resume = await self.resume_repo.get_by_id(resume_id)
        if resume is None:
            return CompactProfile(headline="Unknown Candidate")

        version = await resolve_version(
            self.version_repo, resume_id, version_id=resume_version_id, required=False
        )
        parsed = get_version_content(version) if version else resume.parsed_structure or {}

        profile = CompactProfile()

        # 1. Basic Structure from Resume
        profile.headline = self._extract_headline(parsed, resume)
        profile.skills = [str(s) for s in (parsed.get("skills") or [])]
        profile.education = self._extract_education(parsed)
        profile.certifications = self._extract_certifications(parsed)
        profile.experience_highlights = self._extract_experience(parsed)
        profile.project_highlights = self._extract_projects(parsed)

        # 2. Existing Resume Analysis
        latest_analysis = await self.analysis_repo.get_latest_by_resume(resume_id)
        if latest_analysis:
            status_val = getattr(latest_analysis.status, "value", str(latest_analysis.status))
            if status_val == "completed":
                profile.resume_score = latest_analysis.overall_score

        # 3. Existing Trajectory and Recruiter Lens AI Results
        ai_results = await self.ai_result_repo.list_by_resume(resume_id, limit=20)
        for res in ai_results:
            if res.service_name == AIServiceName.CAREER_TRAJECTORY and res.payload:
                paths = res.payload.get("paths") or []
                profile.trajectory_target_roles = [p.get("role") for p in paths if p.get("role")]
            elif res.service_name == AIServiceName.RECRUITER_LENS and res.payload:
                strengths = res.payload.get("visible_strengths") or []
                profile.recruiter_visible_strengths = [
                    s.get("title") for s in strengths if isinstance(s, dict) and s.get("title")
                ]

        # 4. Existing Job Match (if job_description_id provided or most recent match)
        if job_description_id:
            job_match = await self.match_repo.get_latest_for_pair(
                resume_id, job_description_id, resume_version_id=resume_version_id
            )
            if job_match:
                profile.job_matched_skills = [str(s) for s in (job_match.matched_skills or [])]
                profile.job_missing_skills = [str(s) for s in (job_match.missing_skills or [])]

        # 5. Completed Interview History (if any)
        if resume.user_id:
            sessions = await self.interview_repo.list_by_user(
                resume.user_id, status=InterviewStatus.COMPLETED, limit=5
            )
            for s in sessions:
                if s.report and isinstance(s.report, dict):
                    evals = s.report.get("skill_evaluations") or []
                    for ev in evals:
                        if isinstance(ev, dict) and ev.get("skill"):
                            profile.interview_verified_skills.append(
                                {"skill": ev.get("skill"), "score": ev.get("score", 70)}
                            )


        return profile

    def _extract_headline(self, parsed: dict[str, Any], resume: Resume) -> str:
        summary = parsed.get("professional_summary") or parsed.get("summary") or ""
        if isinstance(summary, str) and summary.strip():
            return summary.split(".")[0].strip()[:100]
        exp = parsed.get("experience") or []
        if exp and isinstance(exp, list) and isinstance(exp[0], dict) and exp[0].get("title"):
            return f"{exp[0].get('title')} professional"
        return resume.title or "Software Professional"

    def _extract_education(self, parsed: dict[str, Any]) -> list[str]:
        items = parsed.get("education") or []
        res = []
        for it in items:
            if isinstance(it, dict):
                degree = it.get("degree") or it.get("title") or ""
                inst = it.get("institution") or it.get("school") or ""
                res.append(f"{degree} ({inst})" if inst else degree)
            elif isinstance(it, str):
                res.append(it)
        return [r for r in res if r]

    def _extract_certifications(self, parsed: dict[str, Any]) -> list[str]:
        items = parsed.get("certifications") or []
        res = []
        for it in items:
            if isinstance(it, dict):
                res.append(str(it.get("name") or it.get("title") or ""))
            elif isinstance(it, str):
                res.append(it)
        return [r for r in res if r]

    def _extract_experience(self, parsed: dict[str, Any]) -> list[dict[str, str]]:
        items = parsed.get("experience") or []
        res = []
        for it in items:
            if isinstance(it, dict):
                res.append(
                    {
                        "title": str(it.get("title") or ""),
                        "organization": str(it.get("organization") or it.get("company") or ""),
                        "description": str(it.get("description") or ""),
                    }
                )
        return res

    def _extract_projects(self, parsed: dict[str, Any]) -> list[dict[str, str]]:
        items = parsed.get("projects") or []
        res = []
        for it in items:
            if isinstance(it, dict):
                res.append(
                    {
                        "title": str(it.get("title") or it.get("name") or ""),
                        "description": str(it.get("description") or ""),
                    }
                )
        return res

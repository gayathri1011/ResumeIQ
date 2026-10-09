"""Career Growth Engine Service.

Pipeline: candidate profile -> target career -> skill gap -> personalized growth plan -> measurable progress.

EVIDENCE WEIGHTING SPECIFICATION:
- 1.00: interview (Rigorous, live technical evaluation under probing questions)
- 0.75: project_evidence (Working repository, test suite, and deliverables)
- 0.50: verified_evidence (Third-party credential, certification, or validated coursework)
- 0.15: self_reported (User milestone checkbox; tracks completion without inflating readiness)
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from app.ai.client import get_ai_service
from app.ai.fallbacks import (
    fallback_career_roadmap,
    fallback_career_skill_gap,
    fallback_project_recommendations,
)
from app.ai.safe_client import RobustAIService
from app.ai.schemas.growth_output import (
    CareerRoadmapOutput,
    CareerSkillGapOutput,
    ProjectRecommendationsOutput,
)
from app.core.database import MongoSession
from app.core.exceptions import AppError
from app.models.enums import GrowthPlanStatus, InterviewStatus
from app.models.growth import (
    CareerGrowthPlan,
    ChangeLogRecord,
    EvidenceEvent,
    ProjectRecommendationRecord,
    RoadmapMilestone,
    RoadmapPhaseRecord,
    SkillGapRecord,
)
from app.models.interview import InterviewSession
from app.repositories.growth_repository import CareerGrowthPlanRepository
from app.repositories.interview_repository import InterviewSessionRepository
from app.schemas.growth import (
    CareerGrowthPlanResponse,
    ChangeLogResponse,
    CreateGrowthPlanRequest,
    EvidenceEventResponse,
    ProjectRecommendationResponse,
    ReadinessOverviewResponse,
    RoadmapMilestoneResponse,
    RoadmapPhaseResponse,
    SkillGapResponse,
    SyncInterviewResultResponse,
    UpdateMilestoneStatusRequest,
)
from app.services.profile_builder import CandidateProfileBuilder, CompactProfile

logger = logging.getLogger(__name__)

# Numeric scale for deterministic computations
LEVEL_POINTS: dict[str, int] = {
    "none": 0,
    "beginner": 25,
    "competent": 60,
    "advanced": 85,
    "expert": 100,
}

IMPORTANCE_WEIGHTS: dict[str, float] = {
    "critical": 3.0,
    "important": 2.0,
    "beneficial": 1.0,
}

EVIDENCE_CLASS_MULTIPLIERS: dict[str, float] = {
    "evidence-backed": 1.00,
    "inferred": 0.65,
    "unverified": 0.35,
    "missing": 0.00,
}

EVIDENCE_TYPE_WEIGHTS: dict[str, float] = {
    "interview": 1.00,
    "project_evidence": 0.75,
    "verified_evidence": 0.50,
    "self_reported": 0.15,
}


def _normalize_token(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _points_to_level(points: float) -> str:
    if points >= 90:
        return "expert"
    if points >= 70:
        return "advanced"
    if points >= 45:
        return "competent"
    if points >= 15:
        return "beginner"
    return "none"


def compute_deterministic_readiness(
    skill_gaps: list[SkillGapRecord],
    evidence_events: list[EvidenceEvent],
) -> int:
    """Deterministically compute overall role readiness percentage (0-100).

    Readiness is calculated as a weighted average over all required skills.
    Self-reported milestone completions (weight 0.15) do NOT inflate the score,
    whereas verified interviews (weight 1.0) and delivered projects (0.75)
    measurably reinforce candidate competency.
    """
    if not skill_gaps:
        return 0

    total_weighted_ratio = 0.0
    total_importance_weight = 0.0

    # Group evidence events by skill token
    events_by_skill: dict[str, list[EvidenceEvent]] = {}
    for ev in evidence_events:
        token = _normalize_token(ev.skill)
        if token:
            events_by_skill.setdefault(token, []).append(ev)

    for sg in skill_gaps:
        imp_weight = IMPORTANCE_WEIGHTS.get(sg.importance.lower(), 2.0)
        req_pts = max(1, LEVEL_POINTS.get(sg.required_level.lower(), 85))
        cur_pts = LEVEL_POINTS.get(sg.current_level.lower(), 0)
        class_mult = EVIDENCE_CLASS_MULTIPLIERS.get(sg.evidence_class.lower(), 0.0)

        # Baseline ratio established from resume evidence
        base_ratio = (cur_pts * class_mult) / req_pts

        # Reinforce with external evidence events if present
        skill_token = _normalize_token(sg.skill)
        events = events_by_skill.get(skill_token, [])
        max_evidence_ratio = 0.0

        for ev in events:
            ev_weight = EVIDENCE_TYPE_WEIGHTS.get(ev.source_type, ev.weight)
            # Self-reported events have a low weight (0.15) and score capped, ensuring no artificial inflation
            normalized_score = (ev.score / 100.0) * ev_weight
            if normalized_score > max_evidence_ratio:
                max_evidence_ratio = normalized_score

        effective_ratio = min(1.0, max(base_ratio, max_evidence_ratio))
        total_weighted_ratio += imp_weight * effective_ratio
        total_importance_weight += imp_weight

    if total_importance_weight <= 0:
        return 0

    return int(round((total_weighted_ratio / total_importance_weight) * 100))


class CareerGrowthService:
    def __init__(
        self,
        session: MongoSession,
        ai_service: RobustAIService | None = None,
    ) -> None:
        self.session = session
        self.repo = CareerGrowthPlanRepository(session)
        self.interview_repo = InterviewSessionRepository(session)
        self.profile_builder = CandidateProfileBuilder(session)
        self.ai_service = (
            ai_service if ai_service is not None else RobustAIService(get_ai_service())
        )

    # ------------------------------------------------------------------
    # Deterministic Skill Classification & Gap Computation
    # ------------------------------------------------------------------
    def classify_skill_from_profile(
        self,
        skill_name: str,
        profile: CompactProfile,
        importance: str = "important",
        required_level: str = "advanced",
    ) -> SkillGapRecord:
        """Classify a target skill into evidence classes and compute gaps deterministically."""
        norm_skill = _normalize_token(skill_name)
        evidence: list[str] = []
        evidence_class = "missing"
        evidence_strength = "none"
        current_level = "none"
        has_skill = False
        verified_in_iv = False
        iv_score: int | None = None

        # 1. Check interview verified competencies (Strongest evidence: 1.0)
        for iv in profile.interview_verified_skills:
            iv_token = _normalize_token(iv.get("skill", ""))
            if norm_skill in iv_token or iv_token in norm_skill:
                score = int(iv.get("score", 70))
                evidence_class = "evidence-backed"
                evidence_strength = "strong"
                has_skill = True
                verified_in_iv = True
                iv_score = score
                if score >= 85:
                    current_level = "advanced"
                elif score >= 65:
                    current_level = "competent"
                else:
                    current_level = "beginner"
                evidence.append(
                    f"Verified in AI technical interview (demonstrated score: {score}%)"
                )
                break

        # 2. Check work experience highlights (Direct practical evidence: evidence-backed)
        if not verified_in_iv:
            for exp in profile.experience_highlights:
                desc = exp.get("description", "") + " " + exp.get("title", "")
                if norm_skill in _normalize_token(desc):
                    evidence_class = "evidence-backed"
                    evidence_strength = "strong"
                    has_skill = True
                    current_level = "competent"
                    org = exp.get("organization") or "prior role"
                    evidence.append(f"Demonstrated in professional work at {org}")
                    break

        # 3. Check portfolio project highlights (Direct practical evidence: evidence-backed)
        if not verified_in_iv and evidence_class == "missing":
            for proj in profile.project_highlights:
                p_text = proj.get("title", "") + " " + proj.get("description", "")
                if norm_skill in _normalize_token(p_text):
                    evidence_class = "evidence-backed"
                    evidence_strength = "moderate"
                    has_skill = True
                    current_level = "competent"
                    evidence.append(f"Applied in portfolio project: {proj.get('title')}")
                    break

        # 4. Check education & certifications (Coursework/academic: inferred)
        if evidence_class == "missing":
            cert_text = " ".join(profile.certifications) + " " + " ".join(profile.education)
            if norm_skill in _normalize_token(cert_text):
                evidence_class = "inferred"
                evidence_strength = "moderate"
                has_skill = True
                current_level = "beginner"
                evidence.append("Referenced in academic curriculum or certification coursework")

        # 5. Check resume skills list alone (Self-reported without role proof: unverified)
        if evidence_class == "missing":
            for sk in profile.skills:
                if norm_skill in _normalize_token(sk) or _normalize_token(sk) in norm_skill:
                    evidence_class = "unverified"
                    evidence_strength = "weak"
                    has_skill = True
                    current_level = "beginner"
                    evidence.append(
                        "Self-listed in resume skills section without contextual project/role evidence"
                    )
                    break

        # 6. Not identified anywhere (missing)
        if evidence_class == "missing":
            evidence_strength = "none"
            current_level = "none"
            has_skill = False
            evidence.append("Not identified in current candidate resume or assessment history")

        # Deterministic Gap calculation
        req_pts = LEVEL_POINTS.get(required_level.lower(), 85)
        cur_pts = LEVEL_POINTS.get(current_level.lower(), 0)
        delta = req_pts - cur_pts

        if delta <= 0:
            gap = "none"
        elif delta <= 25:
            gap = "small"
        elif delta <= 50:
            gap = "medium"
        else:
            gap = "large"

        # Deterministic Priority calculation
        if importance.lower() == "critical" and gap in ("large", "medium"):
            priority = "high"
        elif importance.lower() == "critical" and gap == "small":
            priority = "medium"
        elif importance.lower() == "important" and gap == "large":
            priority = "high"
        elif importance.lower() == "important" and gap in ("medium", "small"):
            priority = "medium"
        elif gap == "none":
            priority = "low"
        else:
            priority = "low"

        # Deterministic Status
        if verified_in_iv or (has_skill and delta <= 0):
            status = "verified"
        elif has_skill:
            status = "in_progress"
        else:
            status = "missing"

        gap_type = "missing_capability" if not has_skill else "proof_gap"

        return SkillGapRecord(
            skill=skill_name,
            required_level=required_level,
            current_level=current_level,
            has_skill=has_skill,
            evidence=evidence,
            evidence_strength=evidence_strength,
            evidence_class=evidence_class,
            importance=importance,
            gap=gap,
            priority=priority,
            status=status,
            gap_type=gap_type,
            why_it_matters=f"Core capability expected for {importance} workflows in target role.",
            target_competency=f"{required_level.title()} competency with verifiable production evidence.",
            verified_in_interview=verified_in_iv,
            latest_interview_score=iv_score,
            evidence_count=len(evidence),
        )

    # ------------------------------------------------------------------
    # Plan Generation & Lifecycle
    # ------------------------------------------------------------------
    async def create_or_get_plan(
        self,
        user_id: uuid.UUID,
        req: CreateGrowthPlanRequest,
    ) -> CareerGrowthPlan:
        """Create a new growth plan or return the active one for the target role."""
        target_role = req.target_role.strip()

        # Check if an active plan already exists for this role
        existing = await self.repo.get_latest_by_user(user_id, target_role=target_role)
        if existing is not None:
            return existing

        # Build candidate profile from existing records (zero expensive re-analysis)
        profile = (
            await self.profile_builder.build_profile(req.resume_id)
            if req.resume_id
            else CompactProfile(headline="Engineering Candidate")
        )

        compact_profile_text = profile.to_compact_text()

        # 1. Propose Skill Gaps via LLM with deterministic fallback
        skill_gap_output = await self.ai_service.run_task(
            prompt_name="career_skill_gap_v1",
            output_schema=CareerSkillGapOutput,
            fallback_factory=lambda: fallback_career_skill_gap(target_role=target_role),
            template_vars={
                "candidate_profile": compact_profile_text,
                "target_role": target_role,
                "target_company": req.target_company or "General Tech",
            },
        )

        # 2. Server deterministically computes levels, evidence classes, gaps, and priorities
        skill_gaps: list[SkillGapRecord] = []
        for item in skill_gap_output.gaps:
            classified = self.classify_skill_from_profile(
                skill_name=item.skill,
                profile=profile,
                importance=getattr(item, "importance", "important"),
                required_level=getattr(item, "required_level", "advanced"),
            )
            classified.why_it_matters = item.why_it_matters
            classified.target_competency = item.expected_competency
            skill_gaps.append(classified)

        # Ensure at least 3 skills exist
        if len(skill_gaps) < 3:
            for extra in ["System Design", "Cloud Infrastructure", "API Architecture"]:
                if not any(_normalize_token(extra) == _normalize_token(s.skill) for s in skill_gaps):
                    skill_gaps.append(
                        self.classify_skill_from_profile(
                            skill_name=extra,
                            profile=profile,
                            importance="important",
                            required_level="advanced",
                        )
                    )

        # 3. Build gap summary for roadmap generator
        gap_lines = [
            f"- {g.skill} (Importance: {g.importance}, Class: {g.evidence_class}, Current: {g.current_level}, Target: {g.required_level}, Priority: {g.priority})"
            for g in skill_gaps
        ]
        diagnosed_gaps_text = "\n".join(gap_lines)

        # 4. Generate Phased Roadmap via LLM with deterministic fallback
        roadmap_output = await self.ai_service.run_task(
            prompt_name="career_roadmap_v1",
            output_schema=CareerRoadmapOutput,
            fallback_factory=lambda: fallback_career_roadmap(target_role=target_role),
            template_vars={
                "candidate_profile": compact_profile_text,
                "target_role": target_role,
                "diagnosed_gaps": diagnosed_gaps_text,
            },
        )

        phases: list[RoadmapPhaseRecord] = []
        for p in roadmap_output.phases:
            phase_milestones: list[RoadmapMilestone] = []
            for m in p.milestones:
                phase_milestones.append(
                    RoadmapMilestone(
                        milestone_id=m.milestone_id,
                        title=m.title,
                        skill=getattr(m, "skill", "") or (m.skills_addressed[0] if m.skills_addressed else ""),
                        why_it_matters=getattr(m, "why_it_matters", "") or f"Addresses readiness for {target_role}.",
                        current_level=getattr(m, "current_level", "none"),
                        target_level=getattr(m, "target_level", "competent"),
                        priority=getattr(m, "priority", "medium"),
                        estimated_effort=getattr(m, "estimated_effort", "1-2 weeks"),
                        prerequisites=getattr(m, "prerequisites", []),
                        recommended_action=getattr(m, "recommended_action", "") or "Implement and review core implementation.",
                        practical_exercise=getattr(m, "practical_exercise", "") or "Build a runnable exercise to verify understanding.",
                        linked_project=getattr(m, "linked_project", None),
                        skills_addressed=m.skills_addressed,
                        deliverable=getattr(m, "deliverable", ""),
                        status="not_started",
                    )
                )
            phases.append(
                RoadmapPhaseRecord(
                    phase_number=p.phase_number,
                    name=p.name,
                    duration_weeks=p.duration_weeks,
                    focus_skills=p.focus_skills,
                    milestones=phase_milestones,
                    learning_objectives=p.learning_objectives,
                )
            )

        # 5. Generate Portfolio Project Recommendations grounded in real gaps
        project_output = await self.ai_service.run_task(
            prompt_name="career_project_recommendations_v1",
            output_schema=ProjectRecommendationsOutput,
            fallback_factory=lambda: fallback_project_recommendations(target_role=target_role),
            template_vars={
                "candidate_profile": compact_profile_text,
                "target_role": target_role,
                "priority_gaps": diagnosed_gaps_text,
            },
        )

        projects: list[ProjectRecommendationRecord] = []
        for pr in project_output.projects:
            projects.append(
                ProjectRecommendationRecord(
                    project_id=pr.project_id,
                    title=pr.title,
                    description=pr.description,
                    why_this_project=getattr(pr, "why_this_project", "") or f"Establishes tangible proof of capability for {target_role}.",
                    gaps_addressed=getattr(pr, "gaps_addressed", []) or pr.targeted_skills,
                    targeted_skills=pr.targeted_skills,
                    suggested_technologies=getattr(pr, "suggested_technologies", []) or ["FastAPI", "Docker", "PostgreSQL"],
                    difficulty=pr.difficulty,
                    architecture_overview=pr.architecture_overview,
                    what_to_implement=getattr(pr, "what_to_implement", "") or "Build core logic, unit tests, and Docker deployment.",
                    key_deliverables=pr.key_deliverables,
                    resume_evidence=getattr(pr, "resume_evidence", "") or pr.resume_bullet_preview,
                    resume_bullet_preview=pr.resume_bullet_preview,
                )
            )

        # 6. Ingest any past completed interviews for this user as initial evidence events
        evidence_events: list[EvidenceEvent] = []
        completed_sessions = await self.interview_repo.list_by_user(
            user_id, status=InterviewStatus.COMPLETED, limit=10
        )
        for s in completed_sessions:
            if s.report and isinstance(s.report, dict):
                skill_evals = s.report.get("skill_evaluations") or []
                for ev in skill_evals:
                    if isinstance(ev, dict) and ev.get("skill"):
                        sk_name = ev.get("skill")
                        score = int(ev.get("score", 70))
                        idemp_key = f"interview:{s.id}:{_normalize_token(sk_name)}"
                        evidence_events.append(
                            EvidenceEvent(
                                source_type="interview",
                                source_id=str(s.id),
                                idempotency_key=idemp_key,
                                skill=sk_name,
                                score=score,
                                weight=1.00,
                                notes=f"Imported from completed interview on {s.target_role}",
                            )
                        )

        # 7. Compute baseline readiness deterministically
        readiness_score = compute_deterministic_readiness(skill_gaps, evidence_events)

        initial_change = ChangeLogRecord(
            change_type="plan_created",
            message=f"Plan initialized for target role {target_role} with baseline readiness {readiness_score}%.",
            affected_skills=[g.skill for g in skill_gaps if g.priority == "high"],
        )

        plan = CareerGrowthPlan(
            user_id=user_id,
            resume_id=req.resume_id,
            resume_version_id=req.resume_version_id,
            target_role=target_role,
            target_company=req.target_company,
            readiness_score=readiness_score,
            status=GrowthPlanStatus.ACTIVE,
            summary=skill_gap_output.summary,
            skill_gaps=skill_gaps,
            roadmap_phases=phases,
            project_recommendations=projects,
            evidence_events=evidence_events,
            change_logs=[initial_change],
            last_evaluated_at=datetime.now(UTC),
        )

        await plan.insert()
        await self.session.flush()
        return plan

    async def get_plan_by_id(
        self,
        plan_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> CareerGrowthPlan:
        plan = await self.repo.get_by_id_and_user(plan_id, user_id)
        if plan is None:
            raise AppError("Growth plan not found.", code="not_found", status_code=404)
        return plan

    async def get_latest_plan(
        self,
        user_id: uuid.UUID,
        target_role: str | None = None,
    ) -> CareerGrowthPlan | None:
        return await self.repo.get_latest_by_user(user_id, target_role=target_role)

    # ------------------------------------------------------------------
    # Progress Tracking & Milestone Updates
    # ------------------------------------------------------------------
    async def update_milestone_status(
        self,
        plan_id: uuid.UUID,
        milestone_id: str,
        user_id: uuid.UUID,
        req: UpdateMilestoneStatusRequest,
    ) -> CareerGrowthPlan:
        """Update roadmap milestone status with evidence type.

        Crucial constraint:
        Clicking 'completed' alone records a self_reported evidence event with weight 0.15,
        which does NOT inflate readiness score directly.
        """
        plan = await self.get_plan_by_id(plan_id, user_id)

        target_milestone: RoadmapMilestone | None = None
        for phase in plan.roadmap_phases:
            for m in phase.milestones:
                if m.milestone_id == milestone_id:
                    target_milestone = m
                    break
            if target_milestone:
                break

        if target_milestone is None:
            raise AppError("Roadmap milestone not found.", code="not_found", status_code=404)

        prev_status = target_milestone.status
        target_milestone.status = req.status
        target_milestone.evidence_type = req.evidence_type or "self_reported"
        target_milestone.notes = req.notes

        if req.status == "completed":
            target_milestone.completed_at = datetime.now(UTC)
            # Log evidence event with appropriate weight
            src_type = req.evidence_type or "self_reported"
            weight = EVIDENCE_TYPE_WEIGHTS.get(src_type, 0.15)
            # Self-reported gets small score weight (20) to prevent score inflation
            event_score = 25 if src_type == "self_reported" else 75
            idemp_key = f"milestone:{milestone_id}:{src_type}:completed"

            if not any(e.idempotency_key == idemp_key for e in plan.evidence_events):
                plan.evidence_events.append(
                    EvidenceEvent(
                        source_type=src_type,
                        source_id=milestone_id,
                        idempotency_key=idemp_key,
                        skill=target_milestone.skill or (target_milestone.skills_addressed[0] if target_milestone.skills_addressed else "Milestone Progress"),
                        score=event_score,
                        weight=weight,
                        notes=f"Milestone '{target_milestone.title}' completed ({src_type})",
                    )
                )
        else:
            target_milestone.completed_at = None

        # Deterministically recompute readiness (which will not jump due to self_reported weight 0.15)
        new_score = compute_deterministic_readiness(plan.skill_gaps, plan.evidence_events)
        plan.readiness_score = new_score
        plan.last_evaluated_at = datetime.now(UTC)

        change_msg = f"Milestone '{target_milestone.title}' status updated from {prev_status} to {req.status} ({req.evidence_type or 'self_reported'}). Readiness: {new_score}%."
        plan.change_logs.append(
            ChangeLogRecord(
                change_type="milestone_update",
                message=change_msg,
                affected_skills=[target_milestone.skill] if target_milestone.skill else target_milestone.skills_addressed,
            )
        )

        await plan.save()
        await self.session.flush()
        return plan

    # ------------------------------------------------------------------
    # Feedback Loop: Interview Ingestion & Synchronisation
    # ------------------------------------------------------------------
    async def sync_interview_session(
        self,
        plan_id: uuid.UUID,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> SyncInterviewResultResponse:
        """Idempotently ingest completed interview results into a growth plan."""
        plan = await self.get_plan_by_id(plan_id, user_id)
        interview = await self.interview_repo.get_by_id_and_user(session_id, user_id)
        if interview is None:
            raise AppError("Interview session not found.", code="not_found", status_code=404)

        return await self._apply_interview_to_plan(plan, interview)

    async def handle_interview_completed(
        self,
        session: InterviewSession,
    ) -> None:
        """Extension point handler called immediately when an interview finishes."""
        try:
            # Look for active plan matching session.target_role or user's latest plan
            plan = await self.repo.get_latest_by_user(
                session.user_id, target_role=session.target_role
            )
            if plan is None:
                plan = await self.repo.get_latest_by_user(session.user_id)

            if plan is not None:
                await self._apply_interview_to_plan(plan, session)
                logger.info(
                    "Growth plan %s updated from completed interview %s",
                    plan.id,
                    session.id,
                )
            else:
                logger.info(
                    "No growth plan exists yet for user %s; interview %s stored for initial plan generation",
                    session.user_id,
                    session.id,
                )
        except Exception:
            logger.exception(
                "Error processing interview completion hook for session %s",
                session.id,
            )

    async def _apply_interview_to_plan(
        self,
        plan: CareerGrowthPlan,
        session: InterviewSession,
    ) -> SyncInterviewResultResponse:
        """Core idempotent feedback loop implementation."""
        report = session.report or {}
        overall_score = session.overall_score or report.get("overall_score") or 70

        # Collect evaluated skills and scores from report + turns
        skill_scores: dict[str, int] = {}
        evaluations = report.get("skill_evaluations") or []
        for ev in evaluations:
            if isinstance(ev, dict) and ev.get("skill"):
                sk = str(ev.get("skill")).strip()
                score = int(ev.get("score", overall_score))
                skill_scores[sk] = score

        # Also inspect turns for tested skill tags
        for t in session.turns:
            if t.turn_score is not None:
                tags = t.skill_tags or ([t.skill_tag] if t.skill_tag else [])
                for tg in tags:
                    norm = tg.strip()
                    if norm and norm not in skill_scores:
                        skill_scores[norm] = t.turn_score

        if not skill_scores:
            skill_scores[session.target_role] = overall_score

        events_added = 0
        affected_skills: list[str] = []

        for skill_name, score in skill_scores.items():
            norm_skill = _normalize_token(skill_name)
            idemp_key = f"interview:{session.id}:{norm_skill}"

            # Check if this evidence event was already ingested (idempotency guarantee)
            if any(e.idempotency_key == idemp_key for e in plan.evidence_events):
                continue

            event = EvidenceEvent(
                source_type="interview",
                source_id=str(session.id),
                idempotency_key=idemp_key,
                skill=skill_name,
                score=score,
                weight=1.00,
                notes=f"Demonstrated in AI Technical Interview ({session.target_role})",
            )
            plan.evidence_events.append(event)
            events_added += 1
            affected_skills.append(skill_name)

            # Update matching skill gap record
            matched_gap = None
            for sg in plan.skill_gaps:
                if (
                    norm_skill in _normalize_token(sg.skill)
                    or _normalize_token(sg.skill) in norm_skill
                ):
                    matched_gap = sg
                    break

            if matched_gap:
                matched_gap.verified_in_interview = True
                matched_gap.latest_interview_score = score
                matched_gap.evidence_class = "evidence-backed"
                matched_gap.evidence_strength = "strong"
                matched_gap.has_skill = True

                # Update demonstrated level based on interview performance
                if score >= 85:
                    matched_gap.current_level = "advanced"
                elif score >= 65:
                    matched_gap.current_level = "competent"
                else:
                    matched_gap.current_level = "beginner"

                # Recompute gap & priority
                req_pts = LEVEL_POINTS.get(matched_gap.required_level.lower(), 85)
                cur_pts = LEVEL_POINTS.get(matched_gap.current_level.lower(), 0)
                delta = req_pts - cur_pts
                matched_gap.gap = "none" if delta <= 0 else ("small" if delta <= 25 else "medium")
                matched_gap.status = "verified" if score >= 65 else "in_progress"
                matched_gap.priority = "low" if delta <= 0 else ("medium" if delta <= 25 else "high")
                date_str = datetime.now(UTC).strftime("%b %d, %Y")
                matched_gap.evidence.append(
                    f"Demonstrated {score}% in live technical interview on {date_str}"
                )

            # Advance associated roadmap milestones if score is solid (>=70)
            if score >= 70:
                for phase in plan.roadmap_phases:
                    for m in phase.milestones:
                        m_token = _normalize_token(m.skill)
                        if m_token and (m_token in norm_skill or norm_skill in m_token):
                            if m.status == "not_started":
                                m.status = "in_progress"

        already_synced = (events_added == 0)
        old_score = plan.readiness_score
        plan.readiness_score = compute_deterministic_readiness(
            plan.skill_gaps, plan.evidence_events
        )
        plan.last_evaluated_at = datetime.now(UTC)

        date_str = datetime.now(UTC).strftime("%b %d, %Y")
        if events_added > 0:
            change_msg = (
                f"Interview on {date_str} evaluated {len(affected_skills)} skills ({', '.join(affected_skills[:3])}). "
                f"Readiness updated from {old_score}% to {plan.readiness_score}%."
            )
            plan.change_logs.append(
                ChangeLogRecord(
                    change_type="interview_sync",
                    message=change_msg,
                    affected_skills=affected_skills,
                )
            )

        await plan.save()
        await self.session.flush()

        return SyncInterviewResultResponse(
            plan_id=plan.id,
            session_id=session.id,
            events_added=events_added,
            updated_readiness_score=plan.readiness_score,
            affected_skills=affected_skills,
            message=(
                f"Successfully synced {events_added} evidence events. Readiness: {plan.readiness_score}%."
                if events_added > 0
                else "Interview session already fully synchronized."
            ),
            already_synced=already_synced,
        )

    # ------------------------------------------------------------------
    # Refresh Plan
    # ------------------------------------------------------------------
    async def refresh_plan(
        self,
        plan_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> CareerGrowthPlan:
        """Recompute readiness score and incorporate all latest evidence."""
        plan = await self.get_plan_by_id(plan_id, user_id)

        # Sync any newly completed interview sessions for this user
        sessions = await self.interview_repo.list_by_user(
            user_id, status=InterviewStatus.COMPLETED, limit=10
        )
        for s in sessions:
            await self._apply_interview_to_plan(plan, s)

        new_readiness = compute_deterministic_readiness(
            plan.skill_gaps, plan.evidence_events
        )
        plan.readiness_score = new_readiness
        plan.last_evaluated_at = datetime.now(UTC)

        plan.change_logs.append(
            ChangeLogRecord(
                change_type="plan_refreshed",
                message=f"Plan refreshed. Verified {len(plan.evidence_events)} evidence events. Readiness: {new_readiness}%.",
                affected_skills=[g.skill for g in plan.skill_gaps if g.status == "verified"],
            )
        )

        await plan.save()
        await self.session.flush()
        return plan

    # ------------------------------------------------------------------
    # Serialization Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def serialize_plan(plan: CareerGrowthPlan) -> CareerGrowthPlanResponse:
        return CareerGrowthPlanResponse(
            id=plan.id,
            user_id=plan.user_id,
            resume_id=plan.resume_id,
            resume_version_id=plan.resume_version_id,
            target_role=plan.target_role,
            target_company=plan.target_company,
            readiness_score=plan.readiness_score,
            status=getattr(plan.status, "value", str(plan.status)),
            summary=plan.summary,
            skill_gaps=[
                SkillGapResponse(
                    skill=sg.skill,
                    required_level=sg.required_level,
                    current_level=sg.current_level,
                    has_skill=sg.has_skill,
                    evidence=sg.evidence,
                    evidence_strength=sg.evidence_strength,
                    evidence_class=sg.evidence_class,
                    importance=sg.importance,
                    gap=sg.gap,
                    priority=sg.priority,
                    status=sg.status,
                    gap_type=sg.gap_type,
                    why_it_matters=sg.why_it_matters,
                    target_competency=sg.target_competency,
                    verified_in_interview=sg.verified_in_interview,
                    latest_interview_score=sg.latest_interview_score,
                    evidence_count=len(sg.evidence),
                )
                for sg in plan.skill_gaps
            ],
            roadmap_phases=[
                RoadmapPhaseResponse(
                    phase_number=p.phase_number,
                    name=p.name,
                    duration_weeks=p.duration_weeks,
                    focus_skills=p.focus_skills,
                    milestones=[
                        RoadmapMilestoneResponse(
                            milestone_id=m.milestone_id,
                            title=m.title,
                            skill=m.skill,
                            why_it_matters=m.why_it_matters,
                            current_level=m.current_level,
                            target_level=m.target_level,
                            priority=m.priority,
                            estimated_effort=m.estimated_effort,
                            prerequisites=m.prerequisites,
                            recommended_action=m.recommended_action,
                            practical_exercise=m.practical_exercise,
                            linked_project=m.linked_project,
                            skills_addressed=m.skills_addressed,
                            deliverable=m.deliverable,
                            status=m.status,
                            completed_at=m.completed_at,
                            evidence_type=m.evidence_type,
                            notes=m.notes,
                        )
                        for m in p.milestones
                    ],
                    learning_objectives=p.learning_objectives,
                )
                for p in plan.roadmap_phases
            ],
            project_recommendations=[
                ProjectRecommendationResponse(
                    project_id=pr.project_id,
                    title=pr.title,
                    description=pr.description,
                    why_this_project=pr.why_this_project,
                    gaps_addressed=pr.gaps_addressed,
                    targeted_skills=pr.targeted_skills,
                    suggested_technologies=pr.suggested_technologies,
                    difficulty=pr.difficulty,
                    architecture_overview=pr.architecture_overview,
                    what_to_implement=pr.what_to_implement,
                    key_deliverables=pr.key_deliverables,
                    resume_evidence=pr.resume_evidence,
                    resume_bullet_preview=pr.resume_bullet_preview,
                )
                for pr in plan.project_recommendations
            ],
            evidence_events=[
                EvidenceEventResponse(
                    event_id=ev.event_id,
                    source_type=ev.source_type,
                    source_id=ev.source_id,
                    idempotency_key=ev.idempotency_key,
                    skill=ev.skill,
                    score=ev.score,
                    weight=ev.weight,
                    notes=ev.notes,
                    recorded_at=ev.recorded_at,
                )
                for ev in plan.evidence_events
            ],
            change_logs=[
                ChangeLogResponse(
                    change_id=c.change_id,
                    timestamp=c.timestamp,
                    change_type=c.change_type,
                    message=c.message,
                    affected_skills=c.affected_skills,
                )
                for c in plan.change_logs
            ],
            last_evaluated_at=plan.last_evaluated_at,
            created_at=plan.created_at,
        )

    def get_readiness_overview(
        self,
        plan: CareerGrowthPlan,
    ) -> ReadinessOverviewResponse:
        evidence_classes_count = {
            "evidence-backed": 0,
            "inferred": 0,
            "unverified": 0,
            "missing": 0,
        }
        priorities_count = {"high": 0, "medium": 0, "low": 0}

        for sg in plan.skill_gaps:
            evidence_classes_count[sg.evidence_class] = (
                evidence_classes_count.get(sg.evidence_class, 0) + 1
            )
            priorities_count[sg.priority] = priorities_count.get(sg.priority, 0) + 1

        serialized = self.serialize_plan(plan)

        return ReadinessOverviewResponse(
            target_role=plan.target_role,
            overall_readiness_score=plan.readiness_score,
            evidence_classes_summary=evidence_classes_count,
            priorities_summary=priorities_count,
            skill_gaps=serialized.skill_gaps,
            weighting_policy=EVIDENCE_TYPE_WEIGHTS,
        )

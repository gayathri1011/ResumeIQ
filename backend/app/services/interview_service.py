from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.ai.client import get_ai_service
from app.ai.fallbacks import (
    fallback_interview_plan,
    fallback_interview_report,
    fallback_interview_turn_eval,
)
from app.ai.safe_client import RobustAIService
from app.ai.schemas.interview_output import (
    InterviewPlanOutput,
    InterviewReportOutput,
    InterviewTurnEvalOutput,
)
from app.core.database import MongoSession
from app.core.exceptions import AppError
from app.models.enums import InterviewStatus
from app.models.interview import InterviewSession, InterviewTurn
from app.repositories.interview_repository import InterviewSessionRepository
from app.schemas.interview import (
    CreateInterviewSessionRequest,
    InterviewReportResponse,
    InterviewSessionListItem,
    InterviewTurnResponse,
    TurnEvaluationResponse,
)
from app.services.profile_builder import CandidateProfileBuilder

logger = logging.getLogger(__name__)

STANDARD_DIMENSIONS = [
    "technical_correctness",
    "relevance",
    "depth",
    "clarity",
    "completeness",
    "reasoning",
    "communication",
    "resume_evidence",
    "role_relevance",
]

REPORT_CATEGORIES = [
    "Technical Knowledge",
    "Project Understanding",
    "Problem Solving",
    "Communication",
    "Role Alignment",
    "Behavioral Readiness",
]


async def on_interview_completed(session: InterviewSession, db_session: MongoSession | None = None) -> None:
    """Internal Phase 3 extension point: Consumed by Career Growth Engine.

    Ingests skill tags, verified scores, and evaluations idempotently into
    the user's growth plan and updates readiness deterministically.
    """
    logger.info(
        "Interview completed hook triggered: session_id=%s, user_id=%s, role=%s, score=%s",
        session.id,
        session.user_id,
        session.target_role,
        session.overall_score,
    )
    try:
        from app.services.growth_service import CareerGrowthService
        growth_svc = CareerGrowthService(session=db_session or MongoSession())
        await growth_svc.handle_interview_completed(session)
    except Exception:
        logger.exception("Error in on_interview_completed hook for session %s", session.id)


class InterviewService:
    def __init__(self, session: MongoSession, ai_service: RobustAIService | None = None) -> None:
        self.session = session
        self.repo = InterviewSessionRepository(session)
        self.profile_builder = CandidateProfileBuilder(session)
        self.ai_service = ai_service if ai_service is not None else RobustAIService(get_ai_service())

    async def create_session(
        self,
        user_id: uuid.UUID,
        req: CreateInterviewSessionRequest,
    ) -> InterviewSession:
        profile_summary = ""
        if req.resume_id:
            try:
                compact = await self.profile_builder.build_profile(
                    req.resume_id,
                    resume_version_id=req.resume_version_id,
                    job_description_id=req.job_description_id,
                )
                profile_summary = json.dumps(compact.model_dump(), default=str)
            except Exception as exc:
                logger.warning("Could not build candidate profile for interview: %s", exc)
                profile_summary = f"Candidate target role: {req.target_role}."
        else:
            profile_summary = f"Candidate target role: {req.target_role}. No stored resume provided."

        combined_focus = list(dict.fromkeys(req.focus_areas + req.focus_skills))
        if req.job_description_text:
            combined_focus.append(f"Target JD Snippet: {req.job_description_text[:300]}")

        plan_inputs = {
            "candidate_profile": profile_summary,
            "target_role": req.target_role,
            "difficulty": req.difficulty,
            "focus_areas": ", ".join(combined_focus) if combined_focus else "Core role competencies",
        }

        plan_output = await self.ai_service.run_task(
            "interview_plan_v1",
            plan_inputs,
            output_schema=InterviewPlanOutput,
            fallback_factory=lambda: fallback_interview_plan(req.target_role, req.difficulty),
        )

        initial_skill_tags = [plan_output.initial_skill_tag]
        if plan_output.focus_skills:
            initial_skill_tags.extend(plan_output.focus_skills[:2])

        turn_0 = InterviewTurn(
            turn_index=0,
            question=plan_output.initial_question,
            skill_tag=plan_output.initial_skill_tag,
            category="technical fundamentals",
            skill_tags=list(dict.fromkeys(initial_skill_tags)),
            question_type=req.interview_type,
            difficulty=req.difficulty,
            expected_criteria=plan_output.initial_expected_criteria,
            user_answer=None,
            answered_at=None,
            turn_score=None,
            evaluation=None,
            is_follow_up=False,
            follow_up_depth=0,
        )

        interview_session = InterviewSession(
            user_id=user_id,
            resume_id=req.resume_id,
            resume_version_id=req.resume_version_id,
            job_description_id=req.job_description_id,
            job_description_text=req.job_description_text,
            target_role=req.target_role,
            difficulty=req.difficulty,
            interview_type=req.interview_type,
            estimated_question_count=max(1, min(10, req.estimated_question_count)),
            focus_areas=req.focus_areas,
            focus_skills=req.focus_skills,
            status=InterviewStatus.IN_PROGRESS,
            plan=plan_output.model_dump(),
            turns=[turn_0],
            current_turn_index=0,
            report=None,
            overall_score=None,
            started_at=datetime.now(UTC),
            completed_at=None,
        )

        await interview_session.insert()
        await self.session.flush()
        return interview_session

    async def get_session(self, session_id: uuid.UUID, user_id: uuid.UUID) -> InterviewSession:
        interview = await self.repo.get_by_id_and_user(session_id, user_id)
        if interview is None:
            raise AppError("Interview session not found.", code="interview_session_not_found", status_code=404)
        return interview

    async def submit_answer(
        self,
        session_id: uuid.UUID,
        turn_index: int,
        answer: str,
        user_id: uuid.UUID,
    ) -> TurnEvaluationResponse:
        interview = await self.get_session(session_id, user_id)

        target_turn = next((t for t in interview.turns if t.turn_index == turn_index), None)
        if target_turn is None:
            raise AppError(f"Interview turn {turn_index} not found.", code="turn_not_found", status_code=404)

        # Double-submit idempotency protection
        if target_turn.user_answer is not None and target_turn.evaluation is not None:
            is_complete = interview.status == InterviewStatus.COMPLETED
            next_turn_resp = None
            if turn_index + 1 < len(interview.turns):
                next_turn_resp = InterviewTurnResponse.model_validate(interview.turns[turn_index + 1].model_dump())
            stored_eval = target_turn.evaluation if isinstance(target_turn.evaluation, dict) else {}
            return TurnEvaluationResponse(
                turn_index=turn_index,
                score=stored_eval.get("score") if stored_eval.get("score") is not None else 7,
                dimension_scores=stored_eval.get("dimension_scores") or {},
                strengths=stored_eval.get("strengths") or [],
                missing_points=stored_eval.get("missing_points") or stored_eval.get("areas_for_improvement") or [],
                feedback=stored_eval.get("feedback") or "",
                next_question_direction=stored_eval.get("next_question_direction") or "",
                resume_claim_status=stored_eval.get("resume_claim_status") or "n/a",
                skill_tags=stored_eval.get("skill_tags") or [],
                is_complete=is_complete,
                next_turn=next_turn_resp,
            )

        if interview.status == InterviewStatus.COMPLETED:
            raise AppError("Interview session is already completed.", code="interview_already_completed", status_code=400)

        remaining_topics = []
        if interview.plan and isinstance(interview.plan, dict):
            remaining_topics = interview.plan.get("question_plan", [])

        eval_inputs = {
            "target_role": interview.target_role,
            "difficulty": target_turn.difficulty,
            "turn_index": target_turn.turn_index + 1,
            "current_question": target_turn.question,
            "skill_tag": target_turn.skill_tag,
            "expected_criteria": json.dumps(target_turn.expected_criteria),
            "candidate_answer": answer,
            "remaining_topics": json.dumps(remaining_topics),
        }

        eval_output = await self.ai_service.run_task(
            "interview_turn_eval_v1",
            eval_inputs,
            output_schema=InterviewTurnEvalOutput,
            fallback_factory=lambda: fallback_interview_turn_eval(
                skill_tag=target_turn.skill_tag,
                current_question=target_turn.question,
            ),
        )

        score = max(0, min(10, eval_output.score))
        dimension_scores = dict(eval_output.dimension_scores)
        for dim in STANDARD_DIMENSIONS:
            if dim not in dimension_scores:
                dimension_scores[dim] = score

        strengths = list(eval_output.strengths)
        missing_points = list(eval_output.missing_points or eval_output.areas_for_improvement)
        feedback = eval_output.feedback or eval_output.interviewer_rationale
        next_direction = eval_output.next_question_direction or eval_output.interviewer_rationale
        resume_claim_status = eval_output.resume_claim_status or "n/a"
        skill_tags = list(eval_output.skill_tags or [target_turn.skill_tag])

        turn_eval_dict = {
            "score": score,
            "dimension_scores": dimension_scores,
            "strengths": strengths,
            "missing_points": missing_points,
            "feedback": feedback,
            "next_question_direction": next_direction,
            "resume_claim_status": resume_claim_status,
            "skill_tags": skill_tags,
        }

        target_turn.user_answer = answer
        target_turn.answered_at = datetime.now(UTC)
        target_turn.turn_score = score * 10
        target_turn.evaluation = turn_eval_dict
        target_turn.strengths = strengths
        target_turn.areas_for_improvement = missing_points
        target_turn.next_action = eval_output.next_action
        target_turn.interviewer_notes = eval_output.interviewer_rationale

        answered_count = sum(1 for t in interview.turns if t.user_answer is not None)
        max_questions = max(1, min(10, interview.estimated_question_count))

        should_terminate = answered_count >= max_questions

        if should_terminate:
            interview.status = InterviewStatus.COMPLETED
            interview.completed_at = datetime.now(UTC)
            report_dict = await self._generate_report(interview)
            interview.report = report_dict
            interview.overall_score = report_dict["overall_score"]
            await self.repo.update(interview)
            await self.session.flush()

            await on_interview_completed(interview, self.session)

            return TurnEvaluationResponse(
                turn_index=turn_index,
                score=score,
                dimension_scores=dimension_scores,
                strengths=strengths,
                missing_points=missing_points,
                feedback=feedback,
                next_question_direction=next_direction,
                resume_claim_status=resume_claim_status,
                skill_tags=skill_tags,
                is_complete=True,
                next_turn=None,
            )

        # Server-enforced adaptive next question rules
        current_follow_up_depth = target_turn.follow_up_depth if target_turn.is_follow_up else 0
        max_follow_ups = 2

        is_follow_up = False
        follow_up_depth = 0
        next_difficulty = interview.difficulty
        next_category = "technical fundamentals"
        next_question_text = ""
        next_skill_tag = target_turn.skill_tag

        if score <= 5:
            # Weak answer: Clarification / fundamentals / easier follow-up
            if current_follow_up_depth < max_follow_ups:
                is_follow_up = True
                follow_up_depth = current_follow_up_depth + 1
                next_category = "weak-area validation"
                next_skill_tag = target_turn.skill_tag
                next_difficulty = "junior" if interview.difficulty in ("mid", "senior") else interview.difficulty
                if eval_output.next_question and len(eval_output.next_question.strip()) > 10:
                    next_question_text = eval_output.next_question.strip()
                else:
                    next_question_text = (
                        f"Could you step back and explain the fundamental core principles of {target_turn.skill_tag} in simple terms?"
                    )
            else:
                # Max follow-up depth reached on this topic; pivot to next planned competency
                is_follow_up = False
                follow_up_depth = 0
                next_category = "role-specific technical"
                planned = self._get_next_planned_question(interview, answered_count)
                next_question_text = planned["question"]
                next_skill_tag = planned["skill_tag"]
        elif score >= 8:
            # Strong answer: Deeper technical, architecture, or scenario question
            is_follow_up = False
            follow_up_depth = 0
            next_category = "scenario" if answered_count % 2 == 1 else "role-specific technical"
            next_difficulty = "senior" if interview.difficulty == "mid" else interview.difficulty
            if eval_output.next_question and len(eval_output.next_question.strip()) > 10:
                next_question_text = eval_output.next_question.strip()
            else:
                planned = self._get_next_planned_question(interview, answered_count)
                next_question_text = (
                    f"Taking {planned['skill_tag']} a step further into production: How would you architect this system to handle high concurrency and automated failure recovery?"
                )
                next_skill_tag = planned["skill_tag"]
        else:
            # Moderate answer (6-7): Progress through planned categories
            is_follow_up = False
            follow_up_depth = 0
            progression_categories = [
                "project",
                "role-specific technical",
                "problem solving",
                "scenario",
                "behavioral",
            ]
            category_idx = min(answered_count - 1, len(progression_categories) - 1)
            next_category = progression_categories[category_idx]
            if eval_output.next_question and len(eval_output.next_question.strip()) > 10:
                next_question_text = eval_output.next_question.strip()
                next_skill_tag = eval_output.next_skill_tag or target_turn.skill_tag
            else:
                planned = self._get_next_planned_question(interview, answered_count)
                next_question_text = planned["question"]
                next_skill_tag = planned["skill_tag"]

        next_turn = InterviewTurn(
            turn_index=len(interview.turns),
            question=next_question_text,
            category=next_category,
            difficulty=next_difficulty,
            skill_tag=next_skill_tag,
            skill_tags=[next_skill_tag],
            question_type=interview.interview_type,
            expected_criteria=[f"Demonstrates clear reasoning in {next_skill_tag}"],
            user_answer=None,
            answered_at=None,
            turn_score=None,
            evaluation=None,
            is_follow_up=is_follow_up,
            follow_up_depth=follow_up_depth,
        )

        interview.turns.append(next_turn)
        interview.current_turn_index = next_turn.turn_index
        await self.repo.update(interview)
        await self.session.flush()

        return TurnEvaluationResponse(
            turn_index=turn_index,
            score=score,
            dimension_scores=dimension_scores,
            strengths=strengths,
            missing_points=missing_points,
            feedback=feedback,
            next_question_direction=next_direction,
            resume_claim_status=resume_claim_status,
            skill_tags=skill_tags,
            is_complete=False,
            next_turn=InterviewTurnResponse.model_validate(next_turn.model_dump()),
        )

    def _get_next_planned_question(
        self,
        interview: InterviewSession,
        answered_count: int,
    ) -> dict[str, str]:
        plan = interview.plan or {}
        question_plan = plan.get("question_plan", [])
        if question_plan and len(question_plan) > 0:
            idx = (answered_count - 1) % len(question_plan)
            item = question_plan[idx]
            topic = item.get("topic", "System Architecture")
            tag = item.get("skill_tag", "Architecture")
            return {
                "question": f"In the domain of {topic}: How do you approach designing and implementing resilient solutions using {tag}?",
                "skill_tag": tag,
            }
        return {
            "question": f"Could you walk through a real-world project where you had to solve a challenging problem in {interview.target_role}?",
            "skill_tag": "Practical Problem Solving",
        }

    async def end_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> InterviewReportResponse:
        interview = await self.get_session(session_id, user_id)
        if interview.report is None:
            interview.status = InterviewStatus.COMPLETED
            if not interview.completed_at:
                interview.completed_at = datetime.now(UTC)
            report_dict = await self._generate_report(interview)
            interview.report = report_dict
            interview.overall_score = report_dict.get("overall_score", 0)
            await self.repo.update(interview)
            await self.session.flush()
            await on_interview_completed(interview, self.session)
        elif interview.status != InterviewStatus.COMPLETED:
            interview.status = InterviewStatus.COMPLETED
            if not interview.completed_at:
                interview.completed_at = datetime.now(UTC)
            await self.repo.update(interview)
            await self.session.flush()

        return InterviewReportResponse.model_validate(interview.report)

    async def get_report(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> InterviewReportResponse:
        interview = await self.get_session(session_id, user_id)
        if interview.report is None:
            # If not generated yet, generate report on-the-fly idempotently
            report_dict = await self._generate_report(interview)
            interview.report = report_dict
            interview.overall_score = report_dict.get("overall_score", 0)
            if interview.status != InterviewStatus.COMPLETED:
                interview.status = InterviewStatus.COMPLETED
                if not interview.completed_at:
                    interview.completed_at = datetime.now(UTC)
            await self.repo.update(interview)
            await self.session.flush()
            await on_interview_completed(interview, self.session)
        return InterviewReportResponse.model_validate(interview.report)

    async def _generate_report(self, interview: InterviewSession) -> dict[str, Any]:
        answered_turns = [
            t for t in interview.turns
            if t.user_answer is not None and t.evaluation is not None
        ]

        # Fast and reliable fallback for sessions ended before answering questions
        if not answered_turns:
            return {
                "session_id": interview.id,
                "target_role": interview.target_role,
                "difficulty": interview.difficulty,
                "overall_score": 0,
                "readiness_status": "needs_work",
                "summary": f"Practice session for {interview.target_role} concluded before questions were answered. Practice at least 1-2 questions to receive detailed feedback.",
                "category_scores": {cat: 0 for cat in REPORT_CATEGORIES},
                "strong_areas": ["Started mock interview session."],
                "weak_areas": ["No answers completed yet."],
                "resume_claims_tested": [],
                "actionable_recommendations": [
                    "Answer at least 1-2 questions to receive in-depth assessment and scoring.",
                    f"Practice key technical concepts for {interview.target_role}.",
                ],
                "ordered_next_practice_areas": ["Core Fundamentals", "Problem Solving"],
                "ordered_practice_areas": ["Core Fundamentals", "Problem Solving"],
                "skill_evaluations": [],
                "skill_scores": {},
                "turns_evaluated": 0,
                "completed_at": interview.completed_at,
            }

        # Deterministic overall readiness /100 aggregation
        turn_scores = [
            ((t.evaluation.get("score") if isinstance(t.evaluation, dict) else 7) or 7) * 10
            for t in answered_turns
        ]
        overall_score = max(0, min(100, round(sum(turn_scores) / len(turn_scores)))) if turn_scores else 0

        if overall_score >= 85:
            readiness_status = "strong_fit"
        elif overall_score >= 75:
            readiness_status = "interview_ready"
        elif overall_score >= 60:
            readiness_status = "progressing"
        else:
            readiness_status = "needs_work"

        # Deterministic category score aggregation from dimensions
        def _avg_dims(*dim_names: str) -> int:
            vals = []
            for t in answered_turns:
                dims = (t.evaluation.get("dimension_scores") if isinstance(t.evaluation, dict) else {}) or {}
                for d in dim_names:
                    if isinstance(dims, dict) and d in dims and dims[d] is not None:
                        try:
                            vals.append(int(dims[d]) * 10)
                        except (ValueError, TypeError):
                            pass
            if not vals:
                return overall_score
            return max(0, min(100, round(sum(vals) / len(vals))))

        category_scores = {
            "Technical Knowledge": _avg_dims("technical_correctness", "depth"),
            "Project Understanding": _avg_dims("resume_evidence", "depth"),
            "Problem Solving": _avg_dims("reasoning", "completeness"),
            "Communication": _avg_dims("communication", "clarity"),
            "Role Alignment": _avg_dims("role_relevance", "relevance"),
            "Behavioral Readiness": _avg_dims("communication", "reasoning", "relevance"),
        }

        # Deterministic tested resume claims
        claims_tested: list[dict[str, Any]] = []
        for t in answered_turns:
            status = (t.evaluation.get("resume_claim_status") if isinstance(t.evaluation, dict) else None) or "n/a"
            if status in ("validated", "weak"):
                claims_tested.append({
                    "claim": f"Tested in Question {t.turn_index + 1} ({t.skill_tag})",
                    "status": status,
                    "evidence": t.user_answer[:150] if t.user_answer else "",
                })

        # Deterministic skill evaluations for Phase 3 Career Growth Engine
        skill_scores_map: dict[str, list[int]] = {}
        for t in answered_turns:
            eval_dict = t.evaluation if isinstance(t.evaluation, dict) else {}
            score_val = ((eval_dict.get("score") if eval_dict else 7) or 7) * 10
            tags = (eval_dict.get("skill_tags") if eval_dict else None) or [t.skill_tag]
            for tag in tags:
                if tag:
                    skill_scores_map.setdefault(tag, []).append(score_val)

        skill_evaluations = [
            {
                "skill": tag,
                "score": round(sum(scores) / len(scores)) if scores else overall_score,
                "evidence_summary": f"Tested in {len(scores)} response(s) with composite average {round(sum(scores) / len(scores)) if scores else overall_score}/100.",
            }
            for tag, scores in skill_scores_map.items()
            if scores
        ]

        # Gather strengths and missing points
        demonstrated_strengths: list[str] = []
        verified_gaps: list[str] = []
        for t in answered_turns:
            eval_dict = t.evaluation if isinstance(t.evaluation, dict) else {}
            for s in (eval_dict.get("strengths") or []):
                if s and s not in demonstrated_strengths:
                    demonstrated_strengths.append(s)
            missing = (eval_dict.get("missing_points") or eval_dict.get("areas_for_improvement") or [])
            for m in (missing or []):
                if m and m not in verified_gaps:
                    verified_gaps.append(m)

        if not demonstrated_strengths:
            demonstrated_strengths = ["Completed mock interview session."]
        if not verified_gaps:
            verified_gaps = ["No critical knowledge deficiencies detected during the session."]

        # Transcript formatted for narrative synthesis
        transcript_lines = []
        for t in answered_turns:
            eval_dict = t.evaluation if isinstance(t.evaluation, dict) else {}
            transcript_lines.append(f"Turn {t.turn_index + 1} [{t.category}] ({t.skill_tag}):")
            transcript_lines.append(f"Q: {t.question}")
            transcript_lines.append(f"A: {t.user_answer}")
            transcript_lines.append(f"Evaluation Score: {eval_dict.get('score', 7)}/10 | Feedback: {eval_dict.get('feedback', '')}")
            transcript_lines.append("")

        transcript_str = "\n".join(transcript_lines) or "Candidate answered questions in mock interview."

        report_inputs = {
            "target_role": interview.target_role,
            "difficulty": interview.difficulty,
            "interview_transcript": transcript_str,
        }

        # Query LLM only for narrative synthesis, but guarantee deterministic scores
        try:
            ai_report = await self.ai_service.run_task(
                "interview_report_v1",
                report_inputs,
                output_schema=InterviewReportOutput,
                fallback_factory=lambda: fallback_interview_report(
                    target_role=interview.target_role,
                    overall_score=overall_score,
                ),
            )
        except Exception as exc:
            logger.warning("AI generation failed for interview report: %s. Using deterministic fallback report.", exc)
            ai_report = fallback_interview_report(
                target_role=interview.target_role,
                overall_score=overall_score,
            )

        narrative_summary = ai_report.summary if ai_report and hasattr(ai_report, "summary") and ai_report.summary else f"Interview session completed for {interview.target_role}."
        raw_recs = []
        if ai_report:
            raw_recs = getattr(ai_report, "actionable_recommendations", None) or getattr(ai_report, "key_recommendations", None) or []
        recommendations = list(dict.fromkeys(raw_recs))
        if not recommendations:
            recommendations = [
                f"Continue practicing structured problem solving and technical depth in {interview.target_role}.",
                "Reinforce production failure modes and trade-off explanations in responses.",
            ]

        raw_ordered = []
        if ai_report:
            raw_ordered = getattr(ai_report, "ordered_next_practice_areas", None) or []
        if not raw_ordered:
            raw_ordered = [t.skill_tag for t in answered_turns if ((t.evaluation.get("score") if isinstance(t.evaluation, dict) else 7) or 7) < 7]
        ordered_practice = list(dict.fromkeys(raw_ordered))
        if not ordered_practice:
            ordered_practice = [t.skill_tag for t in answered_turns[:2] if t.skill_tag] or ["System Reliability", "Core Fundamentals"]

        return {
            "session_id": interview.id,
            "target_role": interview.target_role,
            "difficulty": interview.difficulty,
            "overall_score": overall_score,
            "readiness_status": readiness_status,
            "summary": narrative_summary,
            "category_scores": category_scores,
            "strong_areas": demonstrated_strengths[:5],
            "weak_areas": verified_gaps[:5],
            "resume_claims_tested": claims_tested,
            "actionable_recommendations": recommendations[:4],
            "ordered_next_practice_areas": ordered_practice[:5],
            "ordered_practice_areas": ordered_practice[:5],
            "skill_evaluations": skill_evaluations,
            "skill_scores": {tag: round(sum(scores) / len(scores)) for tag, scores in skill_scores_map.items() if scores},
            "turns_evaluated": len(answered_turns),
            "completed_at": interview.completed_at,
        }

    async def list_sessions(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> list[InterviewSessionListItem]:
        sessions = await self.repo.list_by_user(user_id, skip=skip, limit=limit)
        items: list[InterviewSessionListItem] = []
        for s in sessions:
            answered_turns = sum(1 for t in s.turns if t.user_answer is not None)
            strengths = []
            weaknesses = []
            readiness_status = None
            if s.report:
                strengths = s.report.get("strong_areas", [])[:2]
                weaknesses = s.report.get("weak_areas", [])[:2]
                readiness_status = s.report.get("readiness_status")
            items.append(
                InterviewSessionListItem(
                    id=s.id,
                    target_role=s.target_role,
                    difficulty=s.difficulty,
                    status=s.status.value if hasattr(s.status, "value") else str(s.status),
                    overall_score=s.overall_score,
                    total_turns=len(s.turns),
                    turns_count=len(s.turns),
                    answered_turns=answered_turns,
                    main_strengths=strengths,
                    top_strengths=strengths,
                    main_weaknesses=weaknesses,
                    primary_gaps=weaknesses,
                    readiness_status=readiness_status,
                    created_at=s.created_at,
                    completed_at=s.completed_at,
                )
            )
        return items

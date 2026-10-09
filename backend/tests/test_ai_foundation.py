"""Unit tests for Phase 1 shared foundation:
- Schema validation for all six AI output models
- RobustAIService error & timeout handling -> deterministic fallback
- CandidateProfileBuilder output on sample data
"""

from __future__ import annotations

import asyncio
import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from app.ai.fallbacks import (
    fallback_career_roadmap,
    fallback_career_skill_gap,
    fallback_interview_plan,
    fallback_interview_report,
    fallback_interview_turn_eval,
    fallback_project_recommendations,
)
from app.ai.providers.types import CompletionResult
from app.ai.safe_client import RobustAIService
from app.ai.schemas.growth_output import (
    CareerRoadmapOutput,
    CareerSkillGapOutput,
    ProjectRecommendationsOutput,
)
from app.ai.schemas.interview_output import (
    InterviewPlanOutput,
    InterviewReportOutput,
    InterviewTurnEvalOutput,
)
from app.models.enums import AnalysisStatus
from app.models.resume import Resume
from app.services.profile_builder import CandidateProfileBuilder, CompactProfile



# -------------------------------------------------------------------------
# 1. Pydantic Schema Validation Tests
# -------------------------------------------------------------------------


def test_interview_plan_schema_valid() -> None:
    data = {
        "target_role": "Backend Engineer",
        "difficulty": "mid",
        "estimated_duration_minutes": 30,
        "domains": ["Databases", "APIs"],
        "focus_skills": ["SQL", "FastAPI"],
        "initial_question": "Explain indexing strategies.",
        "initial_skill_tag": "SQL",
        "initial_expected_criteria": ["B-tree vs Hash"],
        "rubric": [{"criterion": "Precision", "description": "Depth", "weight": 50}],
        "question_plan": [
            {
                "topic": "Databases",
                "skill_tag": "SQL",
                "target_competency": "Indexes",
                "difficulty": "mid",
            }
        ],
    }
    model = InterviewPlanOutput.model_validate(data)
    assert model.target_role == "Backend Engineer"
    assert len(model.question_plan) == 1


def test_interview_plan_schema_invalid() -> None:
    # Missing required initial_question and target_role
    with pytest.raises(ValidationError):
        InterviewPlanOutput.model_validate({"difficulty": "mid"})


def test_interview_turn_eval_schema_valid() -> None:
    data = {
        "turn_score": 85,
        "criteria_feedback": [{"criterion": "Clarity", "met": True, "notes": "Good"}],
        "strengths": ["Clear explanation"],
        "areas_for_improvement": ["Add more metrics"],
        "skill_tag_assessments": [
            {"skill": "SQL", "demonstrated_level": "competent", "confidence": 0.9}
        ],
        "next_action": "next_topic",
        "next_question": "Next question text",
        "next_skill_tag": "Docker",
        "interviewer_rationale": "Solid grasp of SQL; moving to deployment.",
    }
    model = InterviewTurnEvalOutput.model_validate(data)
    assert model.turn_score == 85
    assert model.next_action == "next_topic"


def test_interview_report_schema_valid() -> None:
    data = {
        "overall_score": 88,
        "readiness_level": "interview_ready",
        "summary": "Great technical candidate.",
        "category_scores": {"technical": 90, "communication": 85},
        "demonstrated_strengths": ["Deep SQL knowledge"],
        "verified_gaps": ["Kubernetes"],
        "skill_evaluations": [
            {"skill": "SQL", "score": 90, "evidence_summary": "Handled query tuning."}
        ],
        "key_recommendations": ["Review container networking."],
    }
    model = InterviewReportOutput.model_validate(data)
    assert model.overall_score == 88


def test_career_skill_gap_schema_valid() -> None:
    data = {
        "target_role": "Staff Engineer",
        "current_readiness_percentage": 70,
        "summary": "Ready in programming; needs system design proof.",
        "gaps": [
            {
                "skill": "System Design",
                "priority": "high",
                "gap_type": "proof_gap",
                "why_it_matters": "Crucial for staff level.",
                "expected_competency": "Distributed consensus.",
            }
        ],
        "strengths_to_leverage": ["Python expertise"],
    }
    model = CareerSkillGapOutput.model_validate(data)
    assert model.gaps[0].priority == "high"


def test_career_roadmap_schema_valid() -> None:
    data = {
        "target_role": "Backend Engineer",
        "estimated_duration_weeks": 8,
        "summary": "2 phase roadmap.",
        "phases": [
            {
                "phase_number": 1,
                "name": "Phase 1",
                "duration_weeks": 4,
                "focus_skills": ["Docker"],
                "milestones": [
                    {
                        "milestone_id": "m1",
                        "title": "Build image",
                        "skills_addressed": ["Docker"],
                        "deliverable": "Dockerfile",
                    }
                ],
                "learning_objectives": ["Multi-stage builds"],
            }
        ],
    }
    model = CareerRoadmapOutput.model_validate(data)
    assert len(model.phases) == 1


def test_project_recommendations_schema_valid() -> None:
    data = {
        "target_role": "Backend Engineer",
        "summary": "Practical portfolio pieces.",
        "projects": [
            {
                "project_id": "p1",
                "title": "API Gateway",
                "description": "Reverse proxy with rate limiting.",
                "targeted_skills": ["Redis", "FastAPI"],
                "difficulty": "intermediate",
                "architecture_overview": "FastAPI -> Redis",
                "key_deliverables": ["Code", "Docs"],
                "resume_bullet_preview": "Engineered high-throughput API gateway.",
            }
        ],
    }
    model = ProjectRecommendationsOutput.model_validate(data)
    assert model.projects[0].difficulty == "intermediate"


# -------------------------------------------------------------------------
# 2. RobustAIService & Fallback Tests
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_robust_ai_service_fallback_on_empty_response() -> None:
    mock_provider = AsyncMock()
    # Provider returns empty string on first attempt and repair attempt
    mock_provider.complete = AsyncMock(
        return_value=CompletionResult(content="", model_used="mock", token_usage={})
    )

    mock_ai_service = AsyncMock()
    mock_ai_service._provider = mock_provider

    service = RobustAIService(ai_service=mock_ai_service)

    def fallback():
        return fallback_interview_plan("Backend Engineer")

    result, completion = await service.complete_safe(
        prompt="prompt",
        system_prompt="system",
        output_schema=InterviewPlanOutput,
        prompt_version="interview_plan_v1",
        fallback_factory=fallback,
    )

    assert isinstance(result, InterviewPlanOutput)
    assert result.target_role == "Backend Engineer"
    assert "fallback" in completion.model_used


@pytest.mark.asyncio
async def test_robust_ai_service_fallback_on_malformed_json() -> None:
    mock_provider = AsyncMock()
    # Provider returns invalid JSON on both attempts
    mock_provider.complete = AsyncMock(
        return_value=CompletionResult(content="{ not valid json", model_used="mock", token_usage={})
    )

    mock_ai_service = AsyncMock()
    mock_ai_service._provider = mock_provider

    service = RobustAIService(ai_service=mock_ai_service)

    result, completion = await service.complete_safe(
        prompt="prompt",
        system_prompt="system",
        output_schema=InterviewReportOutput,
        prompt_version="interview_report_v1",
        fallback_factory=lambda: fallback_interview_report("Engineer", overall_score=75),
    )

    assert isinstance(result, InterviewReportOutput)
    assert result.overall_score == 75


@pytest.mark.asyncio
async def test_robust_ai_service_timeout_triggers_fallback() -> None:
    async def slow_complete(*args, **kwargs):
        await asyncio.sleep(2.0)
        return CompletionResult(content="{}", model_used="mock", token_usage={})

    mock_provider = AsyncMock()
    mock_provider.complete = slow_complete

    mock_ai_service = AsyncMock()
    mock_ai_service._provider = mock_provider

    service = RobustAIService(ai_service=mock_ai_service)

    result, completion = await service.complete_safe(
        prompt="prompt",
        system_prompt="system",
        output_schema=CareerSkillGapOutput,
        prompt_version="career_skill_gap_v1",
        fallback_factory=lambda: fallback_career_skill_gap("Data Scientist"),
        timeout_seconds=0.1,  # Short timeout for test
    )

    assert isinstance(result, CareerSkillGapOutput)
    assert result.target_role == "Data Scientist"
    assert "timeout" in completion.model_used


@pytest.mark.asyncio
async def test_robust_ai_service_single_repair_recovers_valid_output() -> None:
    valid_data = {
        "target_role": "Backend Engineer",
        "difficulty": "mid",
        "estimated_duration_minutes": 30,
        "domains": ["Databases"],
        "focus_skills": ["Python"],
        "initial_question": "Explain Python generators.",
        "initial_skill_tag": "Python",
        "initial_expected_criteria": ["yield keyword"],
        "rubric": [],
        "question_plan": [],
    }

    mock_provider = AsyncMock()
    # Attempt 1: malformed; Attempt 2 (repair): valid JSON
    mock_provider.complete = AsyncMock(
        side_effect=[
            CompletionResult(content="{ broken json", model_used="mock", token_usage={}),
            CompletionResult(content=json.dumps(valid_data), model_used="mock", token_usage={}),
        ]
    )

    mock_ai_service = AsyncMock()
    mock_ai_service._provider = mock_provider

    service = RobustAIService(ai_service=mock_ai_service)

    result, completion = await service.complete_safe(
        prompt="prompt",
        system_prompt="system",
        output_schema=InterviewPlanOutput,
        prompt_version="interview_plan_v1",
    )

    assert isinstance(result, InterviewPlanOutput)
    assert result.target_role == "Backend Engineer"
    assert mock_provider.complete.call_count == 2


# -------------------------------------------------------------------------
# 3. CandidateProfileBuilder Unit Tests
# -------------------------------------------------------------------------


def test_compact_profile_to_compact_text() -> None:
    profile = CompactProfile(
        headline="Senior Python Engineer",
        skills=["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
        experience_highlights=[
            {
                "title": "Senior Engineer",
                "organization": "Acme Corp",
                "description": "Architected backend microservices processing 50M events daily.",
            }
        ],
        project_highlights=[
            {"title": "Search Engine", "description": "Built vector search retrieval system."}
        ],
        education=["B.S. in Computer Science (MIT)"],
        certifications=["AWS Certified Solutions Architect"],
        resume_score=85,
        trajectory_target_roles=["Lead Backend Engineer", "Staff Engineer"],
        recruiter_visible_strengths=["Strong backend API experience", "High-scale data volume"],
        job_matched_skills=["Python", "PostgreSQL"],
        job_missing_skills=["Kubernetes", "Kafka"],
        interview_verified_skills=[{"skill": "FastAPI", "score": 90}],
    )

    text = profile.to_compact_text(max_chars=2000)

    assert "CURRENT PROFILE: Senior Python Engineer" in text
    assert "RESUME QUALITY SCORE: 85/100" in text
    assert "CORE SKILLS: Python, FastAPI" in text
    assert "RECENT EXPERIENCE:" in text
    assert "KEY PROJECTS:" in text
    assert "B.S. in Computer Science" in text
    assert "AWS Certified Solutions Architect" in text
    assert "KNOWN JOB SKILL GAPS: Kubernetes, Kafka" in text
    assert "VERIFIED INTERVIEW COMPETENCIES: FastAPI: 90%" in text
    assert len(text) < 2000


@pytest.mark.asyncio
async def test_candidate_profile_builder_build_profile() -> None:
    session = AsyncMock()
    builder = CandidateProfileBuilder(session)

    sample_resume_id = uuid.uuid4()
    sample_user_id = uuid.uuid4()

    from types import SimpleNamespace

    mock_resume = SimpleNamespace(
        id=sample_resume_id,
        user_id=sample_user_id,
        title="Python Dev Resume",
        parsed_structure={
            "professional_summary": "Experienced Python Engineer building cloud-native APIs.",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
            "experience": [
                {
                    "title": "Backend Engineer",
                    "organization": "CloudTech",
                    "description": "Built REST APIs with FastAPI.",
                }
            ],
            "projects": [
                {
                    "title": "Event Service",
                    "description": "Async service with Redis Streams.",
                }
            ],
            "education": [{"degree": "B.S. CS", "institution": "Tech University"}],
            "certifications": ["CKA"],
        },
    )


    builder.resume_repo.get_by_id = AsyncMock(return_value=mock_resume)
    builder.version_repo.get_by_id = AsyncMock(return_value=None)

    mock_analysis = AsyncMock()
    mock_analysis.status = AnalysisStatus.COMPLETED
    mock_analysis.overall_score = 82
    builder.analysis_repo.get_latest_by_resume = AsyncMock(return_value=mock_analysis)


    mock_trajectory_res = AsyncMock()
    mock_trajectory_res.service_name = "career_trajectory"
    mock_trajectory_res.payload = {
        "paths": [{"role": "Senior Backend Engineer"}, {"role": "Cloud Architect"}]
    }

    mock_recruiter_res = AsyncMock()
    mock_recruiter_res.service_name = "recruiter_lens"
    mock_recruiter_res.payload = {
        "visible_strengths": [{"title": "FastAPI & Python Foundation"}]
    }

    builder.ai_result_repo.list_by_resume = AsyncMock(
        return_value=[mock_trajectory_res, mock_recruiter_res]
    )

    sample_jd_id = uuid.uuid4()
    mock_match = AsyncMock()
    mock_match.matched_skills = ["Python", "FastAPI"]
    mock_match.missing_skills = ["Kubernetes"]
    builder.match_repo.get_latest_for_pair = AsyncMock(return_value=mock_match)

    mock_interview_session = AsyncMock()
    mock_interview_session.report = {
        "skill_evaluations": [{"skill": "Python", "score": 90}]
    }
    builder.interview_repo.list_by_user = AsyncMock(
        return_value=[mock_interview_session]
    )

    profile = await builder.build_profile(
        sample_resume_id,
        job_description_id=sample_jd_id,
    )

    assert profile.headline == "Experienced Python Engineer building cloud-native APIs"
    assert "Python" in profile.skills
    assert "FastAPI" in profile.skills
    assert profile.resume_score == 82
    assert "Senior Backend Engineer" in profile.trajectory_target_roles
    assert "FastAPI & Python Foundation" in profile.recruiter_visible_strengths
    assert "Kubernetes" in profile.job_missing_skills
    assert profile.interview_verified_skills == [{"skill": "Python", "score": 90}]

    text = profile.to_compact_text()
    assert "CURRENT PROFILE:" in text
    assert "KNOWN JOB SKILL GAPS: Kubernetes" in text
    assert "VERIFIED INTERVIEW COMPETENCIES: Python: 90%" in text


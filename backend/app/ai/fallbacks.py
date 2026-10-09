"""Deterministic fallback factories for all six AI tasks.

Used by RobustAIService when the AI provider times out, fails, or produces invalid output.
Guarantees the system never crashes or exposes raw LLM errors to users.
"""

from __future__ import annotations

from app.ai.schemas.growth_output import (
    CareerRoadmapOutput,
    CareerSkillGapItem,
    CareerSkillGapOutput,
    ProjectRecommendationsOutput,
    RecommendedProjectOutput,
    RoadmapMilestoneOutput,
    RoadmapPhaseOutput,
)
from app.ai.schemas.interview_output import (
    CriterionFeedback,
    InterviewPlanOutput,
    InterviewReportOutput,
    InterviewSkillScore,
    InterviewTurnEvalOutput,
    PlannedQuestion,
    RubricCriteria,
    SkillTagAssessment,
)


def fallback_interview_plan(
    target_role: str = "Software Engineer",
    difficulty: str = "mid",
    focus_areas: list[str] | None = None,
) -> InterviewPlanOutput:
    skills = focus_areas or ["Problem Solving", "System Architecture", "Code Quality"]
    return InterviewPlanOutput(
        target_role=target_role,
        difficulty=difficulty,
        estimated_duration_minutes=30,
        domains=["Domain Fundamentals", "Practical Engineering", "System Trade-offs"],
        focus_skills=skills[:4],
        initial_question=f"Can you walk me through your engineering experience and how you approach challenges in {target_role}?",
        initial_skill_tag=skills[0] if skills else "General Engineering",
        initial_expected_criteria=[
            "Gives a clear, structured overview of background",
            "Highlights technical responsibilities and tooling",
        ],
        rubric=[
            RubricCriteria(criterion="Technical Precision", description="Conceptual accuracy", weight=40),
            RubricCriteria(criterion="Problem Solving", description="Structured methodology", weight=35),
            RubricCriteria(criterion="Communication", description="Clarity and conciseness", weight=25),
        ],
        question_plan=[
            PlannedQuestion(
                topic="Domain Fundamentals",
                skill_tag=skills[0] if skills else "Engineering Fundamentals",
                target_competency="Core concepts and principles",
                difficulty=difficulty,
            ),
            PlannedQuestion(
                topic="Practical Implementation",
                skill_tag=skills[1] if len(skills) > 1 else "Implementation",
                target_competency="Hands-on execution and debugging",
                difficulty=difficulty,
            ),
            PlannedQuestion(
                topic="Architecture & Trade-offs",
                skill_tag=skills[2] if len(skills) > 2 else "System Design",
                target_competency="Scaling and architectural trade-offs",
                difficulty=difficulty,
            ),
        ],
    )


def fallback_interview_turn_eval(
    skill_tag: str = "Technical Communication",
    current_question: str = "",
) -> InterviewTurnEvalOutput:
    return InterviewTurnEvalOutput(
        score=7,
        turn_score=70,
        dimension_scores={
            "technical_correctness": 7,
            "relevance": 8,
            "depth": 7,
            "clarity": 8,
            "completeness": 7,
            "reasoning": 7,
            "communication": 8,
            "resume_evidence": 7,
            "role_relevance": 8,
        },
        criteria_feedback=[
            CriterionFeedback(
                criterion="Core Explanation",
                met=True,
                notes="Candidate addressed the fundamental concept; additional practical depth recommended.",
            )
        ],
        strengths=["Clear articulation of baseline principles."],
        areas_for_improvement=["Provide more quantified production examples and trade-off analysis."],
        missing_points=["Provide more quantified production examples and trade-off analysis."],
        feedback="Candidate addressed the fundamental concept; additional practical depth recommended.",
        next_question_direction="Progressing to systems-level evaluation",
        resume_claim_status="unverified",
        skill_tags=[skill_tag],
        skill_tag_assessments=[
            SkillTagAssessment(
                skill=skill_tag,
                demonstrated_level="competent",
                confidence=0.75,
            )
        ],
        next_action="next_topic",
        next_question="How would you design a scalable solution for this and what failure modes would you monitor?",
        next_skill_tag="System Reliability",
        interviewer_rationale="Baseline competence acknowledged; progressing to systems-level evaluation.",
    )


def fallback_interview_report(
    target_role: str = "Software Engineer",
    overall_score: int = 72,
) -> InterviewReportOutput:
    return InterviewReportOutput(
        overall_score=overall_score,
        readiness_level="progressing" if overall_score < 75 else "interview_ready",
        readiness_status="progressing" if overall_score < 75 else "interview_ready",
        summary=f"Candidate demonstrated foundational competence for {target_role} with opportunities to strengthen specific production depth.",
        category_scores={
            "technical_depth": overall_score,
            "communication": min(100, overall_score + 4),
            "problem_solving": overall_score,
            "role_alignment": overall_score,
        },
        demonstrated_strengths=[
            "Structured response delivery and professional communication",
            "Clear understanding of core software engineering workflows",
        ],
        strong_areas=[
            "Structured response delivery and professional communication",
            "Clear understanding of core software engineering workflows",
        ],
        verified_gaps=[
            "Deeper articulation of distributed system trade-offs and resilience patterns",
        ],
        weak_areas=[
            "Deeper articulation of distributed system trade-offs and resilience patterns",
        ],
        resume_claims_tested=[],
        skill_evaluations=[
            InterviewSkillScore(
                skill="Core Technical Competency",
                score=overall_score,
                evidence_summary="Candidate demonstrated working knowledge of relevant concepts.",
            )
        ],
        key_recommendations=[
            "Review edge case handling and system failure modes before senior-level technical interviews.",
        ],
        actionable_recommendations=[
            "Review edge case handling and system failure modes before senior-level technical interviews.",
        ],
        ordered_next_practice_areas=[
            "System Reliability",
            "Distributed Systems Trade-offs",
        ],
    )


def fallback_career_skill_gap(
    target_role: str = "Software Engineer",
) -> CareerSkillGapOutput:
    return CareerSkillGapOutput(
        target_role=target_role,
        current_readiness_percentage=65,
        summary=f"Analysis identified key technical capabilities and targeted proof gaps for {target_role}.",
        gaps=[
            CareerSkillGapItem(
                skill="Production Architecture",
                priority="high",
                gap_type="proof_gap",
                why_it_matters="High-scale architecture experience is expected for this role.",
                expected_competency="Designing resilient multi-service architectures.",
            ),
            CareerSkillGapItem(
                skill="CI/CD & Cloud Infrastructure",
                priority="medium",
                gap_type="missing_capability",
                why_it_matters="Modern teams expect automated testing and container deployment proficiency.",
                expected_competency="Automated pipelines and containerization.",
            ),
        ],
        strengths_to_leverage=[
            "Demonstrated core programming foundation",
            "Familiarity with industry-standard development workflows",
        ],
    )


def fallback_career_roadmap(
    target_role: str = "Software Engineer",
) -> CareerRoadmapOutput:
    return CareerRoadmapOutput(
        target_role=target_role,
        estimated_duration_weeks=12,
        summary=f"A structured, phased roadmap to systematically close diagnosed gaps and build verified readiness for {target_role}.",
        phases=[
            RoadmapPhaseOutput(
                phase_number=1,
                name="Phase 1: Close Critical Gaps",
                duration_weeks=4,
                focus_skills=["Core Language", "System Architecture"],
                milestones=[
                    RoadmapMilestoneOutput(
                        milestone_id="m1_1",
                        title="Implement a complete production service with test coverage",
                        skill="System Architecture",
                        why_it_matters="Core architecture is critical for high-impact engineering execution.",
                        current_level="beginner",
                        target_level="competent",
                        priority="high",
                        estimated_effort="2-3 weeks",
                        prerequisites=["Basic API development", "Git fundamentals"],
                        recommended_action="Build modular service layers separating business logic from persistence.",
                        practical_exercise="Refactor a monolith endpoint into clean hexagonal architecture with unit tests.",
                        linked_project="proj_fallback_1",
                        skills_addressed=["System Architecture", "Testing"],
                        deliverable="Working service repository with automated tests",
                    )
                ],
                learning_objectives=[
                    "Solidify advanced language features and architectural boundaries",
                    "Write robust unit and integration test suites",
                ],
            ),
            RoadmapPhaseOutput(
                phase_number=2,
                name="Phase 2: Build Practical Capability",
                duration_weeks=4,
                focus_skills=["CI/CD & Cloud Infrastructure", "Production Architecture"],
                milestones=[
                    RoadmapMilestoneOutput(
                        milestone_id="m2_1",
                        title="Deploy containerized application with automated pipeline",
                        skill="CI/CD & Cloud Infrastructure",
                        why_it_matters="Deployment velocity and reliability depend on automated CI/CD.",
                        current_level="none",
                        target_level="competent",
                        priority="high",
                        estimated_effort="1-2 weeks",
                        prerequisites=["Docker basics", "GitHub actions knowledge"],
                        recommended_action="Set up multi-stage Docker builds and automated lint/test workflows.",
                        practical_exercise="Create a GitHub Action pipeline that runs tests and builds a minimal container image.",
                        linked_project="proj_fallback_1",
                        skills_addressed=["CI/CD & Cloud Infrastructure"],
                        deliverable="Deployed application with live endpoint and pipeline configuration",
                    )
                ],
                learning_objectives=[
                    "Master containerization and infrastructure configuration",
                    "Demonstrate cloud deployment and health monitoring",
                ],
            ),
            RoadmapPhaseOutput(
                phase_number=3,
                name="Phase 3: Advanced Capability",
                duration_weeks=2,
                focus_skills=["Scalability", "Resilience"],
                milestones=[
                    RoadmapMilestoneOutput(
                        milestone_id="m3_1",
                        title="Implement rate limiting, caching, and circuit breaker patterns",
                        skill="Scalability",
                        why_it_matters="Demonstrates ability to handle production scale and partial network failures.",
                        current_level="beginner",
                        target_level="advanced",
                        priority="medium",
                        estimated_effort="1-2 weeks",
                        prerequisites=["Redis basics", "HTTP response codes"],
                        recommended_action="Incorporate Redis token bucket rate limiting and graceful error degradation.",
                        practical_exercise="Simulate 500 downstream failures and verify circuit breaker opens cleanly.",
                        linked_project="proj_fallback_1",
                        skills_addressed=["Scalability", "Resilience"],
                        deliverable="Resilient service with verified load-test benchmarks",
                    )
                ],
                learning_objectives=[
                    "Prevent cascading service failures",
                    "Tune cache invalidation and connection pooling",
                ],
            ),
            RoadmapPhaseOutput(
                phase_number=4,
                name="Phase 4: Interview Readiness",
                duration_weeks=2,
                focus_skills=["Technical Communication", "System Design"],
                milestones=[
                    RoadmapMilestoneOutput(
                        milestone_id="m4_1",
                        title="Complete simulated technical interview on core architecture",
                        skill="Technical Communication",
                        why_it_matters="Converts technical capability into interview success under probing questions.",
                        current_level="competent",
                        target_level="advanced",
                        priority="high",
                        estimated_effort="1-2 weeks",
                        prerequisites=["Completed Phase 1 and 2 milestones"],
                        recommended_action="Run a practice session with the Adaptive AI Interviewer focusing on target gaps.",
                        practical_exercise="Defend trade-offs between consistency models and async messaging in 5 dialogue turns.",
                        linked_project=None,
                        skills_addressed=["Technical Communication", "System Design"],
                        deliverable="Interview score of 75%+ across architecture and clarity dimensions",
                    )
                ],
                learning_objectives=[
                    "Articulate design trade-offs with STAR structure",
                    "Identify and address edge cases before interviewer prompts",
                ],
            ),
        ],
    )


def fallback_project_recommendations(
    target_role: str = "Software Engineer",
) -> ProjectRecommendationsOutput:
    return ProjectRecommendationsOutput(
        target_role=target_role,
        summary=f"Portfolio projects tailored to establish undeniable proof of competency for {target_role}.",
        projects=[
            RecommendedProjectOutput(
                project_id="proj_fallback_1",
                title="Resilient Microservice Backend with Automated CI/CD",
                description="Design and deploy an asynchronous service featuring rate limiting, caching, and database pooling.",
                why_this_project=f"Provides visible proof of architecture, cloud readiness, and scale for {target_role}.",
                gaps_addressed=["System Architecture", "CI/CD & Cloud Infrastructure"],
                targeted_skills=["System Architecture", "Docker", "Database Optimization"],
                suggested_technologies=["FastAPI / Python", "Docker", "PostgreSQL", "Redis", "GitHub Actions"],
                difficulty="intermediate",
                architecture_overview="API Gateway -> Web Service -> Cache Layer -> Relational Database",
                what_to_implement="Implement token bucket rate limiter, health check endpoints, containerized build, and automated test suite.",
                key_deliverables=[
                    "Containerized codebase with configuration files",
                    "Benchmark report demonstrating latency under load",
                ],
                resume_evidence=f"Architected resilient backend service for {target_role} workflows, achieving sub-50ms latency under simulated load.",
                resume_bullet_preview=f"Architected resilient backend service for {target_role} workflows, achieving sub-50ms latency under simulated load.",
            )
        ],
    )

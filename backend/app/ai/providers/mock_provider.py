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


def _is_trajectory_prompt(messages: list[dict[str, str]] | None) -> bool:
    if not messages:
        return False
    combined = " ".join(message.get("content", "") for message in messages).lower()
    return "career trajectory" in combined or "trajectory" in combined and "current_profile" in combined


def _is_recruiter_lens_prompt(messages: list[dict[str, str]] | None) -> bool:
    if not messages:
        return False
    combined = " ".join(message.get("content", "") for message in messages).lower()
    return "10-second" in combined or "recruiter lens" in combined


def _build_valid_recruiter_lens_output(messages: list[dict[str, str]] | None = None) -> dict[str, object]:
    return {
        "recruiter_snapshot": {
            "target_role": "Software Engineer",
            "experience": "Recent software engineering experience",
            "strongest_skills": ["Python", "SQL", "REST APIs"],
            "domain": "Backend software development",
            "differentiator": "Backend API and service experience supported by a technical project.",
        },
        "first_impression": "A software engineering candidate with visible backend development, API, and database experience. The technical foundation is clear, while measurable outcomes could be easier to spot.",
        "clarity": "The recent engineering title and backend skills create a recognizable direction in a quick scan.",
        "visible_strengths": [
            {"title": "Relevant technical stack", "evidence": "Python, SQL, and REST APIs are listed in the resume skills."},
            {"title": "Backend project evidence", "evidence": "The resume includes a project demonstrating API or service work."},
        ],
        "potentially_missed": [
            {"title": "Outcomes may be buried", "evidence": "Technical descriptions are present, but measurable outcomes are not prominent in the parsed content."},
        ],
        "risks": [
            {"issue": "Impact is not immediately quantified", "reason": "The resume contains limited measurable results in experience or project descriptions."},
        ],
        "improvements": [
            {"action": "Move one strongest backend outcome into the opening summary or first experience bullet.", "reason": "This would make the existing technical evidence easier to recognize in a fast scan."},
            {"action": "Add metrics where they already exist in the candidate's records.", "reason": "The resume currently emphasizes implementation more than visible results."},
        ],
        "current_positioning": "Software engineer with backend API and database experience.",
        "recommended_positioning": "Backend-focused software engineer specializing in Python APIs and data-backed services.",
        "limitations": ["This is a structural resume heuristic, not real recruiter eye-tracking or a hiring prediction."],
    }


def _build_valid_trajectory_output(messages: list[dict[str, str]] | None = None) -> dict[str, object]:
    return {
        "current_profile": "Software Engineer",
        "profile_summary": "The resume shows software engineering experience supported by backend development and API work.",
        "paths": [
            {
                "role": "Backend Engineer",
                "timeframe": "Now to 1 year",
                "required_skills": ["Python", "SQL", "REST APIs"],
                "experience_signals": ["backend services", "API design"],
                "seniority_level": "mid",
                "role_fit_reason": "This is the closest adjacent move because the resume already shows backend services and API development.",
                "resume_evidence": ["Built backend services with Python and PostgreSQL."],
                "likely_skill_gaps": ["Cloud deployment"],
                "likely_proof_gaps": ["Quantified production impact"],
                "next_steps": ["Add a measured outcome to an existing backend project.", "Document one deployed API project end to end."],
            },
            {
                "role": "Full Stack Engineer",
                "timeframe": "1 to 2 years",
                "required_skills": ["Python", "React", "REST APIs"],
                "experience_signals": ["frontend and backend delivery"],
                "seniority_level": "mid",
                "role_fit_reason": "The resume can extend its engineering foundation into full stack delivery where frontend evidence is present.",
                "resume_evidence": ["The resume includes API and application development experience."],
                "likely_skill_gaps": ["Production frontend ownership"],
                "likely_proof_gaps": ["End-to-end feature ownership"],
                "next_steps": ["Ship one project that connects a frontend to an existing API."],
            },
        ],
        "limitations": ["Readiness reflects resume evidence and does not measure performance in a real hiring process."],
    }


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


def _is_interview_plan_prompt(messages: list[dict[str, str]] | None) -> bool:
    if not messages:
        return False
    combined = " ".join(message.get("content", "") for message in messages).lower()
    return "interview plan" in combined or "adaptive ai interview architect" in combined


def _build_valid_interview_plan_output(messages: list[dict[str, str]] | None = None) -> dict[str, object]:
    user_text = messages[-1].get("content", "") if messages else ""
    role = "Backend Engineer"
    difficulty = "mid"
    if "TARGET ROLE:" in user_text:
        try:
            line = [ln for ln in user_text.splitlines() if "TARGET ROLE:" in ln][0]
            extracted = line.split("TARGET ROLE:", 1)[1].strip()
            if extracted:
                role = extracted
        except Exception:
            pass
    if "DIFFICULTY:" in user_text:
        try:
            line = [ln for ln in user_text.splitlines() if "DIFFICULTY:" in ln][0]
            extracted = line.split("DIFFICULTY:", 1)[1].strip()
            if extracted:
                difficulty = extracted
        except Exception:
            pass

    is_genai = "genai" in role.lower() or "ai" in role.lower() or "llm" in role.lower()
    is_frontend = "frontend" in role.lower() or "react" in role.lower()

    if is_genai:
        domains = ["LLM Architecture", "RAG Systems", "Evaluation & Safety"]
        focus_skills = ["Prompt Engineering", "Vector DBs", "LangChain/LlamaIndex"]
        initial_q = f"How would you evaluate and optimize a RAG pipeline for the {role} position?"
        initial_tag = "RAG Pipelines"
    elif is_frontend:
        domains = ["UI Engineering", "State Management", "Performance"]
        focus_skills = ["React", "TypeScript", "Core Web Vitals"]
        initial_q = f"How do you profile and optimize client-side rendering performance for {role}?"
        initial_tag = "React Performance"
    else:
        domains = ["Backend Systems", "API Design", "Databases"]
        focus_skills = ["Python", "SQL", "System Design"]
        initial_q = f"Can you explain how you design a resilient REST API endpoint handling database transactions for a {role}?"
        initial_tag = "API Design"

    return {
        "target_role": role,
        "difficulty": difficulty,
        "estimated_duration_minutes": 30,
        "domains": domains,
        "focus_skills": focus_skills,
        "initial_question": initial_q,
        "initial_skill_tag": initial_tag,
        "initial_expected_criteria": [
            "Clear technical rationale and trade-offs",
            "Production failure mode mitigation",
        ],
        "rubric": [
            {"criterion": "Technical Precision", "description": "Accuracy and depth", "weight": 40},
            {"criterion": "Problem Solving", "description": "Trade-offs and edge cases", "weight": 35},
            {"criterion": "Communication", "description": "Clarity and conciseness", "weight": 25},
        ],
        "question_plan": [
            {
                "topic": domains[0],
                "skill_tag": focus_skills[0],
                "target_competency": "Domain fundamentals",
                "difficulty": difficulty,
            },
            {
                "topic": domains[1] if len(domains) > 1 else domains[0],
                "skill_tag": focus_skills[1] if len(focus_skills) > 1 else focus_skills[0],
                "target_competency": "Practical implementation and tradeoffs",
                "difficulty": difficulty,
            },
            {
                "topic": domains[2] if len(domains) > 2 else domains[0],
                "skill_tag": focus_skills[2] if len(focus_skills) > 2 else focus_skills[0],
                "target_competency": "Production architecture and scaling",
                "difficulty": difficulty,
            },
        ],
    }


def _is_interview_turn_eval_prompt(messages: list[dict[str, str]] | None) -> bool:
    if not messages:
        return False
    combined = " ".join(message.get("content", "") for message in messages).lower()
    return "interview evaluator" in combined or "evaluate this interview turn" in combined


def _build_valid_interview_turn_eval_output(messages: list[dict[str, str]] | None = None) -> dict[str, object]:
    user_text = messages[-1].get("content", "") if messages else ""
    answer_text = ""
    if "<candidate_answer>" in user_text and "</candidate_answer>" in user_text:
        answer_text = user_text.split("<candidate_answer>")[1].split("</candidate_answer>")[0].strip()

    is_weak = any(phrase in answer_text.lower() for phrase in ["not sure", "don't know", "unsure", "i guess", "no idea"]) or (len(answer_text) > 0 and len(answer_text) < 25)
    is_strong = any(phrase in answer_text.lower() for phrase in ["deep", "architecture", "tradeoff", "trade-off", "idempotent", "distributed", "benchmarked", "sharding", "consistency"]) or len(answer_text) > 200

    if is_weak:
        score = 4
        turn_score = 40
        dim_scores = {
            "technical_correctness": 4, "relevance": 5, "depth": 3, "clarity": 5,
            "completeness": 3, "reasoning": 4, "communication": 5, "resume_evidence": 4, "role_relevance": 5
        }
        strengths = ["Willingness to acknowledge knowledge boundary."]
        missing = ["Missing fundamental definition and core conceptual principles."]
        feedback = "Answer lacked depth on foundational principles; stepping back to clarify core concepts."
        next_action = "follow_up"
        next_q = "Could you explain the basic core concepts or fundamental principles behind this approach?"
        next_tag = "Fundamentals Clarification"
        rationale = "Candidate demonstrated uncertainty; providing an accessible follow-up to validate fundamentals."
        claim_status = "weak"
    elif is_strong:
        score = 9
        turn_score = 90
        dim_scores = {
            "technical_correctness": 9, "relevance": 9, "depth": 9, "clarity": 9,
            "completeness": 9, "reasoning": 9, "communication": 9, "resume_evidence": 9, "role_relevance": 9
        }
        strengths = ["Comprehensive domain depth, precise trade-off evaluation, and production mindset."]
        missing = []
        feedback = "Excellent response demonstrating senior-level technical judgment and clear communication."
        next_action = "next_topic"
        next_q = "Given that architecture, how would you design for high availability and failover across multiple regions?"
        next_tag = "Distributed Architecture"
        rationale = "Candidate provided an outstanding answer; escalating to deeper scenario and architecture."
        claim_status = "validated"
    else:
        score = 8
        turn_score = 80
        dim_scores = {
            "technical_correctness": 8, "relevance": 8, "depth": 8, "clarity": 8,
            "completeness": 8, "reasoning": 8, "communication": 8, "resume_evidence": 8, "role_relevance": 8
        }
        strengths = ["Solid explanation of core concepts and structured communication."]
        missing = ["Could provide more quantified production metrics."]
        feedback = "Good response covering key aspects with clear structure."
        next_action = "next_topic"
        next_q = "How do you approach indexing and query optimization when response latency degrades under high load?"
        next_tag = "SQL Optimization"
        rationale = "Strong answer; advancing to practical performance tuning."
        claim_status = "validated"

    return {
        "score": score,
        "turn_score": turn_score,
        "dimension_scores": dim_scores,
        "criteria_feedback": [
            {
                "criterion": "Technical Correctness",
                "met": not is_weak,
                "notes": feedback,
            }
        ],
        "strengths": strengths,
        "areas_for_improvement": missing,
        "missing_points": missing,
        "feedback": feedback,
        "next_question_direction": rationale,
        "resume_claim_status": claim_status,
        "skill_tags": [next_tag],
        "skill_tag_assessments": [
            {
                "skill": next_tag,
                "demonstrated_level": "advanced" if is_strong else ("beginner" if is_weak else "competent"),
                "confidence": 0.85,
            }
        ],
        "next_action": next_action,
        "next_question": next_q,
        "next_skill_tag": next_tag,
        "interviewer_rationale": rationale,
    }


def _is_interview_report_prompt(messages: list[dict[str, str]] | None) -> bool:
    if not messages:
        return False
    combined = " ".join(message.get("content", "") for message in messages).lower()
    return "interview evaluation panel" in combined or "final interview report" in combined


def _build_valid_interview_report_output(messages: list[dict[str, str]] | None = None) -> dict[str, object]:
    return {
        "overall_score": 84,
        "readiness_level": "interview_ready",
        "readiness_status": "interview_ready",
        "summary": "Candidate demonstrated solid domain competencies with clear communication and structured problem solving across interview turns.",
        "category_scores": {
            "Technical Knowledge": 85,
            "Project Understanding": 84,
            "Problem Solving": 84,
            "Communication": 82,
            "Role Alignment": 86,
            "Behavioral Readiness": 80,
            "technical_depth": 85,
            "communication": 82,
            "problem_solving": 84,
            "role_alignment": 86,
        },
        "demonstrated_strengths": [
            "Robust mental model of system boundaries and API design",
            "Clear articulation of data management strategies",
        ],
        "strong_areas": [
            "Robust mental model of system boundaries and API design",
            "Clear articulation of data management strategies",
        ],
        "verified_gaps": [
            "Limited discussion of distributed tracing and multi-cluster observability",
        ],
        "weak_areas": [
            "Limited discussion of distributed tracing and multi-cluster observability",
        ],
        "resume_claims_tested": [
            {"claim": "Engineered high-performance REST APIs", "status": "validated"},
            {"claim": "Managed distributed SQL transactions", "status": "validated"},
        ],
        "skill_evaluations": [
            {
                "skill": "API Design",
                "score": 88,
                "evidence_summary": "Articulated idempotency and transaction boundaries effectively.",
            },
            {
                "skill": "SQL Optimization",
                "score": 80,
                "evidence_summary": "Explained composite indexes and execution plan profiling.",
            },
        ],
        "key_recommendations": [
            "Review distributed consensus and caching invalidation strategies for senior-level interviews.",
        ],
        "actionable_recommendations": [
            "Review distributed consensus and caching invalidation strategies for senior-level interviews.",
        ],
        "ordered_next_practice_areas": [
            "Distributed Tracing & Observability",
            "Multi-region consensus",
        ],
    }


def _is_career_skill_gap_prompt(messages: list[dict[str, str]] | None) -> bool:
    if not messages:
        return False
    combined = " ".join(message.get("content", "") for message in messages).lower()
    return "skill gap strategist" in combined or "career skill-gap" in combined


def _build_valid_career_skill_gap_output() -> dict[str, object]:
    return {
        "target_role": "Backend Engineer",
        "current_readiness_percentage": 68,
        "summary": "Strong foundational programming and database knowledge; gaps exist in distributed systems and cloud deployment proof.",
        "gaps": [
            {
                "skill": "Docker",
                "priority": "high",
                "gap_type": "missing_capability",
                "why_it_matters": "Containerization is required for modern microservices delivery.",
                "expected_competency": "Multi-stage builds and container networking.",
            },
            {
                "skill": "System Design",
                "priority": "medium",
                "gap_type": "proof_gap",
                "why_it_matters": "Needs concrete evidence of scaling services beyond single-node instances.",
                "expected_competency": "Caching architectures and message queues.",
            },
        ],
        "strengths_to_leverage": [
            "Extensive Python development background",
            "Relational database query and schema proficiency",
        ],
    }


def _is_career_roadmap_prompt(messages: list[dict[str, str]] | None) -> bool:
    if not messages:
        return False
    combined = " ".join(message.get("content", "") for message in messages).lower()
    return "career roadmap architect" in combined or "phased career growth roadmap" in combined


def _build_valid_career_roadmap_output() -> dict[str, object]:
    return {
        "target_role": "Backend Engineer",
        "estimated_duration_weeks": 8,
        "summary": "An 8-week targeted curriculum focusing on containerization, asynchronous messaging, and production deployments.",
        "phases": [
            {
                "phase_number": 1,
                "name": "Containerization & Workflows",
                "duration_weeks": 4,
                "focus_skills": ["Docker", "CI/CD"],
                "milestones": [
                    {
                        "milestone_id": "m1_1",
                        "title": "Containerize a multi-tier web application",
                        "skills_addressed": ["Docker"],
                        "deliverable": "Working Dockerfile and docker-compose setup with healthchecks",
                    }
                ],
                "learning_objectives": [
                    "Master multi-stage Docker builds",
                    "Configure local networking between API and database",
                ],
            },
            {
                "phase_number": 2,
                "name": "Distributed Messaging & Scaling",
                "duration_weeks": 4,
                "focus_skills": ["System Design", "Redis"],
                "milestones": [
                    {
                        "milestone_id": "m2_1",
                        "title": "Implement asynchronous background workers",
                        "skills_addressed": ["System Design", "Redis"],
                        "deliverable": "Task queue worker service with retry semantics",
                    }
                ],
                "learning_objectives": [
                    "Design decoupled message architectures",
                    "Handle idempotency and consumer backpressure",
                ],
            },
        ],
    }


def _is_career_project_recommendations_prompt(messages: list[dict[str, str]] | None) -> bool:
    if not messages:
        return False
    combined = " ".join(message.get("content", "") for message in messages).lower()
    return "technical project advisor" in combined or "proof-building portfolio projects" in combined


def _build_valid_career_project_recommendations_output() -> dict[str, object]:
    return {
        "target_role": "Backend Engineer",
        "summary": "Selected projects establish tangible proof for distributed systems and containerization.",
        "projects": [
            {
                "project_id": "proj_1",
                "title": "Event-Driven Asynchronous Ingestion Pipeline",
                "description": "A production-grade ingestion service handling webhooks and dispatching to background workers.",
                "targeted_skills": ["Docker", "Redis", "FastAPI"],
                "difficulty": "intermediate",
                "architecture_overview": "FastAPI API Gateway -> Redis Streams -> Python Worker Pool -> PostgreSQL",
                "key_deliverables": [
                    "Repository with docker-compose and load testing script",
                    "Documented architecture diagram and benchmark results",
                ],
                "resume_bullet_preview": "Engineered asynchronous ingestion pipeline using FastAPI, Redis Streams, and Docker, processing 1,500 events/sec with zero message drop.",
            }
        ],
    }


def _resolve_mock_output(messages: list[dict[str, str]] | None) -> dict[str, object]:
    if _is_interview_plan_prompt(messages):
        return _build_valid_interview_plan_output(messages)
    if _is_interview_turn_eval_prompt(messages):
        return _build_valid_interview_turn_eval_output(messages)
    if _is_interview_report_prompt(messages):
        return _build_valid_interview_report_output(messages)
    if _is_career_skill_gap_prompt(messages):
        return _build_valid_career_skill_gap_output()
    if _is_career_roadmap_prompt(messages):
        return _build_valid_career_roadmap_output()
    if _is_career_project_recommendations_prompt(messages):
        return _build_valid_career_project_recommendations_output()
    if _is_resume_optimize_prompt(messages):
        return _build_valid_resume_optimize_output(messages)
    if _is_skill_gap_prompt(messages):
        return _build_valid_skill_gap_output(messages)
    if _is_trajectory_prompt(messages):
        return _build_valid_trajectory_output(messages)
    if _is_recruiter_lens_prompt(messages):
        return _build_valid_recruiter_lens_output(messages)
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
            elif _is_skill_gap_prompt(messages):
                bad["missing_skill_explanations"] = "not-a-list"
            elif _is_trajectory_prompt(messages):
                bad["paths"] = []
            elif _is_recruiter_lens_prompt(messages):
                bad["first_impression"] = ""
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

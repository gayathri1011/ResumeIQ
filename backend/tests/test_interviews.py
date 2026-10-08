from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.client import AIService
from app.ai.providers.mock_provider import MockAIProvider
from app.core.database import MongoSession, get_async_session
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.enums import InterviewStatus
from app.models.interview import InterviewSession, InterviewTurn
from app.repositories import ResumeRepository, UserRepository
from app.schemas.interview import CreateInterviewSessionRequest
from app.services.interview_service import InterviewService
from tests.test_job_matching import SAMPLE_RESUME_PARSED


@pytest.mark.asyncio
async def test_interview_plan_personalized_by_role(db_session: MongoSession) -> None:
    user = await UserRepository(db_session).create(
        email=f"plan-{uuid.uuid4()}@example.com",
        password_hash=hash_password("SecurePass123"),
    )

    with patch("app.services.interview_service.get_ai_service") as mock_get:
        mock_get.return_value = AIService(provider=MockAIProvider())
        service = InterviewService(db_session)

        req_genai = CreateInterviewSessionRequest(
            target_role="Junior GenAI Engineer",
            difficulty="junior",
            focus_skills=["LLMs", "RAG"],
        )
        session_genai = await service.create_session(user.id, req_genai)

        req_frontend = CreateInterviewSessionRequest(
            target_role="Senior Frontend Engineer",
            difficulty="senior",
            focus_skills=["React", "TypeScript"],
        )
        session_frontend = await service.create_session(user.id, req_frontend)

    assert session_genai.target_role == "Junior GenAI Engineer"
    assert session_frontend.target_role == "Senior Frontend Engineer"
    assert session_genai.plan is not None
    assert session_frontend.plan is not None
    assert session_genai.plan["initial_skill_tag"] != session_frontend.plan["initial_skill_tag"]
    initial_q_genai = str(session_genai.plan["initial_question"]).lower()
    assert "rag" in initial_q_genai or "genai" in initial_q_genai or "ai" in initial_q_genai
    initial_q_frontend = str(session_frontend.plan["initial_question"]).lower()
    assert "frontend" in initial_q_frontend or "react" in initial_q_frontend


@pytest.mark.asyncio
async def test_adaptive_loop_weak_answer_triggers_clarification(db_session: MongoSession) -> None:
    user = await UserRepository(db_session).create(
        email=f"weak-{uuid.uuid4()}@example.com",
        password_hash=hash_password("SecurePass123"),
    )

    with patch("app.services.interview_service.get_ai_service") as mock_get:
        mock_get.return_value = AIService(provider=MockAIProvider())
        service = InterviewService(db_session)
        req = CreateInterviewSessionRequest(
            target_role="Backend Engineer",
            difficulty="mid",
        )
        session = await service.create_session(user.id, req)

        # Weak answer containing uncertainty keywords
        res = await service.submit_answer(
            session_id=session.id,
            turn_index=0,
            answer="I'm not sure how this works, honestly no idea.",
            user_id=user.id,
        )

    assert res.score <= 5
    assert res.is_complete is False
    assert res.next_turn is not None
    assert res.next_turn.is_follow_up is True
    assert res.next_turn.category == "weak-area validation"


@pytest.mark.asyncio
async def test_adaptive_loop_strong_answer_triggers_deeper_question(db_session: MongoSession) -> None:
    user = await UserRepository(db_session).create(
        email=f"strong-{uuid.uuid4()}@example.com",
        password_hash=hash_password("SecurePass123"),
    )

    with patch("app.services.interview_service.get_ai_service") as mock_get:
        mock_get.return_value = AIService(provider=MockAIProvider())
        service = InterviewService(db_session)
        req = CreateInterviewSessionRequest(
            target_role="Backend Engineer",
            difficulty="mid",
        )
        session = await service.create_session(user.id, req)

        # Strong answer with architectural depth
        strong_answer = (
            "We enforce idempotency by using unique idempotency keys in Redis with atomic SETNX. "
            "For database consistency, we isolate transactions with Serializable isolation where required, "
            "implementing exponential backoff retries for deadlock mitigation. "
            "We carefully evaluate the trade-off between consistency and latency."
        )
        res = await service.submit_answer(
            session_id=session.id,
            turn_index=0,
            answer=strong_answer,
            user_id=user.id,
        )

    assert res.score >= 8
    assert res.is_complete is False
    assert res.next_turn is not None
    assert res.next_turn.difficulty == "senior"
    assert res.next_turn.category in ("scenario", "role-specific technical")


@pytest.mark.asyncio
async def test_limits_and_termination_respected(db_session: MongoSession) -> None:
    user = await UserRepository(db_session).create(
        email=f"limits-{uuid.uuid4()}@example.com",
        password_hash=hash_password("SecurePass123"),
    )

    with patch("app.services.interview_service.get_ai_service") as mock_get:
        mock_get.return_value = AIService(provider=MockAIProvider())
        service = InterviewService(db_session)
        req = CreateInterviewSessionRequest(
            target_role="Backend Engineer",
            difficulty="mid",
            estimated_question_count=4,
        )
        session = await service.create_session(user.id, req)

        # Answer 4 turns sequentially (the clamped minimum limit)
        for turn_idx in range(4):
            res = await service.submit_answer(
                session_id=session.id,
                turn_index=turn_idx,
                answer="We design clean REST APIs with structured JSON schema and comprehensive error handling.",
                user_id=user.id,
            )
            if turn_idx < 3:
                assert res.is_complete is False
            else:
                assert res.is_complete is True
                assert res.next_turn is None

        # Verify session is marked completed with report
        updated = await service.get_session(session.id, user.id)
        assert updated.status == InterviewStatus.COMPLETED
        assert updated.overall_score is not None
        assert updated.report is not None


@pytest.mark.asyncio
async def test_malformed_llm_output_triggers_fallback_safely(db_session: MongoSession) -> None:
    user = await UserRepository(db_session).create(
        email=f"malformed-{uuid.uuid4()}@example.com",
        password_hash=hash_password("SecurePass123"),
    )

    # Mock provider returning invalid JSON on first call
    malformed_provider = MockAIProvider(invalid_json=True)
    with patch("app.services.interview_service.get_ai_service") as mock_get:
        mock_get.return_value = AIService(provider=malformed_provider)
        service = InterviewService(db_session)
        req = CreateInterviewSessionRequest(
            target_role="Site Reliability Engineer",
            difficulty="senior",
        )
        session = await service.create_session(user.id, req)

    # Should not crash; fallback plan created
    assert session.status == InterviewStatus.IN_PROGRESS
    assert len(session.turns) == 1
    assert session.turns[0].question != ""


@pytest.mark.asyncio
async def test_deterministic_report_score_aggregation(db_session: MongoSession) -> None:
    user = await UserRepository(db_session).create(
        email=f"report-{uuid.uuid4()}@example.com",
        password_hash=hash_password("SecurePass123"),
    )

    # Construct session with known turn scores (9, 7) -> deterministic average (90 + 70)/2 = 80
    turn_1 = InterviewTurn(
        turn_index=0,
        question="Question 1",
        skill_tag="API Design",
        category="technical fundamentals",
        user_answer="Answer 1",
        turn_score=90,
        evaluation={
            "score": 9,
            "dimension_scores": {
                "technical_correctness": 9, "relevance": 9, "depth": 9, "clarity": 9,
                "completeness": 9, "reasoning": 9, "communication": 9, "resume_evidence": 9, "role_relevance": 9
            },
            "strengths": ["Strong architectural insight"],
            "missing_points": [],
            "feedback": "Great",
            "next_question_direction": "Next",
            "resume_claim_status": "validated",
            "skill_tags": ["API Design"],
        },
    )
    turn_2 = InterviewTurn(
        turn_index=1,
        question="Question 2",
        skill_tag="SQL",
        category="role-specific technical",
        user_answer="Answer 2",
        turn_score=70,
        evaluation={
            "score": 7,
            "dimension_scores": {
                "technical_correctness": 7, "relevance": 7, "depth": 7, "clarity": 7,
                "completeness": 7, "reasoning": 7, "communication": 7, "resume_evidence": 7, "role_relevance": 7
            },
            "strengths": ["Working knowledge"],
            "missing_points": ["Could profile execution plan"],
            "feedback": "Decent",
            "next_question_direction": "Next",
            "resume_claim_status": "unverified",
            "skill_tags": ["SQL"],
        },
    )

    session = InterviewSession(
        user_id=user.id,
        target_role="Backend Engineer",
        difficulty="mid",
        status=InterviewStatus.IN_PROGRESS,
        turns=[turn_1, turn_2],
    )
    await session.insert()
    await db_session.flush()

    with patch("app.services.interview_service.get_ai_service") as mock_get:
        mock_get.return_value = AIService(provider=MockAIProvider())
        service = InterviewService(db_session)
        report_resp = await service.end_session(session.id, user.id)

    # Deterministic overall score must be exactly (90 + 70) / 2 = 80
    assert report_resp.overall_score == 80
    assert report_resp.category_scores["Technical Knowledge"] == 80
    assert report_resp.readiness_status in ("interview_ready", "strong_fit")
    assert report_resp.turns_evaluated == 2


@pytest.mark.asyncio
async def test_double_submit_protection_idempotent(db_session: MongoSession) -> None:
    user = await UserRepository(db_session).create(
        email=f"idempotent-{uuid.uuid4()}@example.com",
        password_hash=hash_password("SecurePass123"),
    )

    with patch("app.services.interview_service.get_ai_service") as mock_get:
        mock_get.return_value = AIService(provider=MockAIProvider())
        service = InterviewService(db_session)
        req = CreateInterviewSessionRequest(target_role="Backend Engineer")
        session = await service.create_session(user.id, req)

        res_first = await service.submit_answer(
            session_id=session.id,
            turn_index=0,
            answer="First submission of answer.",
            user_id=user.id,
        )

        # Second submission to same turn
        res_second = await service.submit_answer(
            session_id=session.id,
            turn_index=0,
            answer="Duplicate submit attempt.",
            user_id=user.id,
        )

    # Both return the exact same score and feedback
    assert res_first.score == res_second.score
    assert res_first.feedback == res_second.feedback

    # Turns list did NOT create a duplicated turn
    refreshed = await service.get_session(session.id, user.id)
    assert len(refreshed.turns) == 2  # Turn 0 + next Turn 1


@pytest.mark.asyncio
async def test_authorization_user_cannot_access_other_sessions(db_session: MongoSession) -> None:
    async def override_session() -> AsyncGenerator[MongoSession, None]:
        yield db_session

    app.dependency_overrides[get_async_session] = override_session

    user_a = await UserRepository(db_session).create(
        email=f"usera-{uuid.uuid4()}@example.com",
        password_hash=hash_password("SecurePass123"),
    )
    user_b = await UserRepository(db_session).create(
        email=f"userb-{uuid.uuid4()}@example.com",
        password_hash=hash_password("SecurePass123"),
    )
    await db_session.flush()

    token_a, _ = create_access_token(user_a.id)
    token_b, _ = create_access_token(user_b.id)

    with patch("app.services.interview_service.get_ai_service") as mock_get:
        mock_get.return_value = AIService(provider=MockAIProvider())
        service = InterviewService(db_session)
        session_a = await service.create_session(
            user_a.id,
            CreateInterviewSessionRequest(target_role="Backend Engineer"),
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User B tries to read User A's session -> 404
        resp = await client.get(
            f"/api/v1/interviews/sessions/{session_a.id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp.status_code == 404

        # User B tries to submit an answer to User A's session -> 404
        resp_ans = await client.post(
            f"/api/v1/interviews/sessions/{session_a.id}/turns/0/answer",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"answer": "Hacked answer"},
        )
        assert resp_ans.status_code == 404

        # User B tries to end User A's session -> 404
        resp_end = await client.post(
            f"/api/v1/interviews/sessions/{session_a.id}/end",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp_end.status_code == 404

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_unauthenticated_requests_rejected() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/interviews/sessions")
        assert resp.status_code == 401

        resp = await client.post(
            "/api/v1/interviews/sessions",
            json={"target_role": "Backend Engineer"},
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_all_endpoints_contract_flow(db_session: MongoSession) -> None:
    async def override_session() -> AsyncGenerator[MongoSession, None]:
        yield db_session

    app.dependency_overrides[get_async_session] = override_session

    user = await UserRepository(db_session).create(
        email=f"e2e-{uuid.uuid4()}@example.com",
        password_hash=hash_password("SecurePass123"),
    )
    token, _ = create_access_token(user.id)

    with patch("app.services.interview_service.get_ai_service") as mock_get:
        mock_get.return_value = AIService(provider=MockAIProvider())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {token}"}

            # 1. POST /sessions
            create_resp = await client.post(
                "/api/v1/interviews/sessions",
                headers=headers,
                json={
                    "target_role": "Staff Backend Engineer",
                    "difficulty": "senior",
                    "estimated_question_count": 4,
                },
            )
            assert create_resp.status_code == 201
            session_data = create_resp.json()
            session_id = session_data["id"]
            assert session_data["target_role"] == "Staff Backend Engineer"
            assert session_data["current_question"] is not None

            # 2. GET /sessions
            list_resp = await client.get("/api/v1/interviews/sessions", headers=headers)
            assert list_resp.status_code == 200
            items = list_resp.json()
            assert len(items) >= 1
            assert items[0]["id"] == session_id

            # 3. GET /sessions/{session_id}
            get_resp = await client.get(f"/api/v1/interviews/sessions/{session_id}", headers=headers)
            assert get_resp.status_code == 200
            assert get_resp.json()["id"] == session_id

            # 4. POST /sessions/{session_id}/turns/0/answer
            ans_resp = await client.post(
                f"/api/v1/interviews/sessions/{session_id}/turns/0/answer",
                headers=headers,
                json={"answer": "We manage distributed transactions using Saga choreography with Kafka topics."},
            )
            assert ans_resp.status_code == 200
            eval_data = ans_resp.json()
            assert "score" in eval_data
            assert "feedback" in eval_data
            assert eval_data["is_complete"] is False

            # 5. POST /sessions/{session_id}/end
            end_resp = await client.post(
                f"/api/v1/interviews/sessions/{session_id}/end",
                headers=headers,
            )
            assert end_resp.status_code == 200
            report_data = end_resp.json()
            assert report_data["overall_score"] > 0
            assert report_data["summary"]
            assert "category_scores" in report_data

            # 6. GET /sessions/{session_id}/report
            report_get_resp = await client.get(
                f"/api/v1/interviews/sessions/{session_id}/report",
                headers=headers,
            )
            assert report_get_resp.status_code == 200
            assert report_get_resp.json()["session_id"] == session_id

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_two_question_end_to_end_flow(db_session: MongoSession) -> None:
    async def override_session() -> AsyncGenerator[MongoSession, None]:
        yield db_session

    app.dependency_overrides[get_async_session] = override_session

    user = await UserRepository(db_session).create(
        email=f"e2e-2q-{uuid.uuid4()}@example.com",
        password_hash=hash_password("SecurePass123"),
    )
    token, _ = create_access_token(user.id)

    with patch("app.services.interview_service.get_ai_service") as mock_get:
        mock_get.return_value = AIService(provider=MockAIProvider())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {token}"}

            # 1. POST /sessions with estimated_question_count = 2
            create_resp = await client.post(
                "/api/v1/interviews/sessions",
                headers=headers,
                json={
                    "target_role": "Frontend Architect",
                    "difficulty": "senior",
                    "interview_type": "technical",
                    "estimated_question_count": 2,
                    "focus_skills": ["React", "Performance"],
                },
            )
            assert create_resp.status_code == 201
            session_data = create_resp.json()
            session_id = session_data["id"]
            assert session_data["target_role"] == "Frontend Architect"
            assert session_data["current_question"] is not None

            # 2. Answer question 1 (turn 0)
            ans1_resp = await client.post(
                f"/api/v1/interviews/sessions/{session_id}/turns/0/answer",
                headers=headers,
                json={"answer": "We manage client state with Zustand and render static content at edge."},
            )
            assert ans1_resp.status_code == 200
            eval1 = ans1_resp.json()
            assert "score" in eval1
            assert "feedback" in eval1
            assert eval1["is_complete"] is False

            # 3. Answer question 2 (turn 1) - reaches 2 questions!
            ans2_resp = await client.post(
                f"/api/v1/interviews/sessions/{session_id}/turns/1/answer",
                headers=headers,
                json={"answer": "We optimize Core Web Vitals through code splitting and asset compression."},
            )
            assert ans2_resp.status_code == 200
            eval2 = ans2_resp.json()
            assert "score" in eval2
            assert "feedback" in eval2
            assert eval2["is_complete"] is True

            # 4. GET report
            report_resp = await client.get(
                f"/api/v1/interviews/sessions/{session_id}/report",
                headers=headers,
            )
            assert report_resp.status_code == 200
            report = report_resp.json()
            assert report["session_id"] == session_id
            assert report["overall_score"] > 0
            assert len(report["ordered_practice_areas"]) > 0

            # 5. GET history list
            list_resp = await client.get("/api/v1/interviews/sessions", headers=headers)
            assert list_resp.status_code == 200
            items = list_resp.json()
            assert len(items) >= 1
            matching = next(i for i in items if i["id"] == session_id)
            assert matching["turns_count"] == 2
            assert matching["status"] == "completed"

            # 6. Reopen report
            reopen_resp = await client.get(
                f"/api/v1/interviews/sessions/{session_id}/report",
                headers=headers,
            )
            assert reopen_resp.status_code == 200
            assert reopen_resp.json()["overall_score"] == report["overall_score"]

    app.dependency_overrides.clear()

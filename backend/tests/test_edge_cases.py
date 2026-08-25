"""Cross-feature edge case tests for Phase 17."""

from __future__ import annotations

import copy
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.client import AIService
from app.ai.providers.mock_provider import MockAIProvider
from app.ai.tasks.job_matcher import JobMatcher
from app.core.config import settings
from app.core.database import get_async_session
from app.main import app
from app.models.enums import ResumeVersionSource, ResumeVersionStatus
from app.repositories import JobDescriptionRepository, ResumeRepository, ResumeVersionRepository
from app.services.embedding_service import semantic_similarity_score
from tests.fixtures.auth import auth_headers, signup_user
from tests.test_job_analysis import SAMPLE_JD
from tests.test_job_matching import SAMPLE_RESUME_PARSED, UNRELATED_RESUME_PARSED


@pytest.fixture
async def auth_client(db_session) -> AsyncClient:
    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def test_zero_skill_overlap_still_returns_score() -> None:
    vector_a = [1.0, 0.0, 0.0]
    vector_b = [0.0, 1.0, 0.0]
    assert semantic_similarity_score(vector_a, vector_b) == 50.0


@pytest.mark.asyncio
async def test_single_section_resume_can_be_parsed(sample_pdf) -> None:
    from app.parsers.registry import parse_resume_file

    result = parse_resume_file(sample_pdf, "sample_resume.pdf", "application/pdf")
    assert result.structured.experience is not None
    assert isinstance(result.structured.meta.sections_missing, list)


@pytest.mark.asyncio
async def test_match_with_unrelated_resume(auth_client: AsyncClient, db_session) -> None:
    _, token = await signup_user(auth_client)
    user_response = await auth_client.get("/api/v1/auth/me", headers=auth_headers(token))
    user_id = user_response.json()["id"]

    resume_repo = ResumeRepository(db_session)
    job_repo = JobDescriptionRepository(db_session)
    version_repo = ResumeVersionRepository(db_session)

    resume = await resume_repo.create(
        user_id=user_id,
        title="Unrelated Resume",
        parsed_structure=copy.deepcopy(UNRELATED_RESUME_PARSED),
        raw_text="Retail associate",
        content_embedding=[0.0] * settings.embedding_dimensions,
    )
    await version_repo.create(
        resume_id=resume.id,
        version_number=1,
        label="Original",
        content_snapshot=copy.deepcopy(UNRELATED_RESUME_PARSED),
        source=ResumeVersionSource.UPLOAD,
        status=ResumeVersionStatus.ACTIVE,
    )

    job = await job_repo.create(
        user_id=user_id,
        title="Senior Software Engineer",
        raw_text=SAMPLE_JD,
        parsed_requirements={
            "job_title": "Senior Software Engineer",
            "required_skills": ["Python", "SQL"],
            "preferred_skills": [],
            "technologies": ["FastAPI"],
            "keywords": ["microservices"],
        },
        content_embedding=[0.1] * settings.embedding_dimensions,
    )

    matcher = JobMatcher(AIService(provider=MockAIProvider()), db_session)
    with patch.object(matcher.embedding_service, "ensure_resume_embedding", return_value=[0.0] * settings.embedding_dimensions):
        result = await matcher.match(resume.id, job.id, user_id=user_id)

    assert result["overall_score"] >= 0
    assert "matched_skills" in result


@pytest.mark.asyncio
async def test_delete_version_cleans_referencing_records(auth_client: AsyncClient, db_session) -> None:
    from app.models.analysis import Recommendation, ResumeAnalysis
    from app.models.enums import AnalysisStatus, RecommendationSourceType
    from app.models.job import JobMatch

    _, token = await signup_user(auth_client)
    user_response = await auth_client.get("/api/v1/auth/me", headers=auth_headers(token))
    user_id = user_response.json()["id"]

    resume_repo = ResumeRepository(db_session)
    version_repo = ResumeVersionRepository(db_session)
    resume = await resume_repo.create(
        user_id=user_id,
        title="Version Cleanup",
        parsed_structure=copy.deepcopy(SAMPLE_RESUME_PARSED),
    )
    version_a = await version_repo.create(
        resume_id=resume.id,
        version_number=1,
        label="Original",
        content_snapshot=copy.deepcopy(SAMPLE_RESUME_PARSED),
        source=ResumeVersionSource.UPLOAD,
        status=ResumeVersionStatus.ACTIVE,
    )
    version_b = await version_repo.create(
        resume_id=resume.id,
        version_number=2,
        label="Duplicate",
        content_snapshot=copy.deepcopy(SAMPLE_RESUME_PARSED),
        source=ResumeVersionSource.MANUAL,
        status=ResumeVersionStatus.ACTIVE,
    )

    analysis = ResumeAnalysis(
        resume_id=resume.id,
        resume_version_id=version_b.id,
        status=AnalysisStatus.COMPLETED,
        overall_score=70,
        category_scores={},
        issues=[],
    )
    db_session.add(analysis)
    await db_session.flush()

    job_repo = JobDescriptionRepository(db_session)
    job = await job_repo.create(
        user_id=user_id,
        title="Engineer JD",
        raw_text=SAMPLE_JD,
        parsed_requirements={"job_title": "Engineer"},
    )

    match = JobMatch(
        resume_id=resume.id,
        resume_version_id=version_b.id,
        job_description_id=job.id,
        overall_score=55,
        breakdown={},
        matched_skills=[],
        missing_skills=[],
    )
    db_session.add(match)
    await db_session.flush()

    recommendation = Recommendation(
        resume_id=resume.id,
        job_match_id=match.id,
        source_type=RecommendationSourceType.JOB_MATCH,
        category="skill_gap",
        title="Learn Python",
        description="Add Python projects.",
        priority=1,
    )
    db_session.add(recommendation)
    await db_session.flush()

    response = await auth_client.delete(
        f"/api/v1/resumes/{resume.id}/versions/{version_b.id}",
        headers=auth_headers(token),
    )
    assert response.status_code == 200

    assert await db_session.get(ResumeAnalysis, analysis.id) is None
    assert await db_session.get(JobMatch, match.id) is None
    assert await db_session.get(Recommendation, recommendation.id) is None
    assert await db_session.get(type(version_a), version_a.id) is not None


@pytest.mark.asyncio
async def test_sparse_resume_pdf_generation(auth_client: AsyncClient, db_session) -> None:
    from tests.test_pdf_generation import SPARSE_RESUME_PARSED

    _, token = await signup_user(auth_client)
    user_response = await auth_client.get("/api/v1/auth/me", headers=auth_headers(token))
    user_id = user_response.json()["id"]

    resume_repo = ResumeRepository(db_session)
    version_repo = ResumeVersionRepository(db_session)
    resume = await resume_repo.create(
        user_id=user_id,
        title="Sparse Resume",
        parsed_structure=copy.deepcopy(SPARSE_RESUME_PARSED),
        raw_text="Early-career software developer.",
    )
    version = await version_repo.create(
        resume_id=resume.id,
        version_number=1,
        label="Sparse",
        content_snapshot=copy.deepcopy(SPARSE_RESUME_PARSED),
        source=ResumeVersionSource.UPLOAD,
        status=ResumeVersionStatus.ACTIVE,
    )

    response = await auth_client.post(
        f"/api/v1/resumes/{resume.id}/versions/{version.id}/generate",
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) > 100

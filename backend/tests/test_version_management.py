"""Tests for resume version management."""

from __future__ import annotations

import copy

import pytest
from app.core.exceptions import AppError

from app.models.analysis import AIAnalysisResult, Recommendation, ResumeAnalysis
from app.models.enums import AnalysisStatus, RecommendationSourceType, ResumeVersionSource, ResumeVersionStatus
from app.models.job import JobMatch
from app.core.security import hash_password
from app.repositories import (
    JobDescriptionRepository,
    ResumeAnalysisRepository,
    ResumeRepository,
    ResumeVersionRepository,
    UserRepository,
)
from app.services.version_service import VersionService
from tests.test_job_matching import SAMPLE_RESUME_PARSED


async def _create_test_user(db_session):
    from uuid import uuid4

    user_repo = UserRepository(db_session)
    return await user_repo.create(
        email=f"version-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("SecurePass123"),
        full_name="Version Tester",
    )


@pytest.mark.asyncio
async def test_create_duplicate_version_starts_unanalyzed(db_session) -> None:
    resume_repo = ResumeRepository(db_session)
    version_repo = ResumeVersionRepository(db_session)
    analysis_repo = ResumeAnalysisRepository(db_session)
    service = VersionService(db_session)

    user = await _create_test_user(db_session)

    resume = await resume_repo.create(
        user_id=user.id,
        title="Version Parent",
        parsed_structure=copy.deepcopy(SAMPLE_RESUME_PARSED),
        raw_text="resume",
    )
    source = await version_repo.create(
        resume_id=resume.id,
        version_number=1,
        label="Original",
        content_snapshot=copy.deepcopy(SAMPLE_RESUME_PARSED),
        raw_text="resume",
        source=ResumeVersionSource.UPLOAD,
        status=ResumeVersionStatus.ACTIVE,
    )
    await analysis_repo.create(
        resume_id=resume.id,
        resume_version_id=source.id,
        overall_score=80,
        status=AnalysisStatus.COMPLETED,
    )
    await db_session.flush()

    duplicated = await service.create_version(
        resume.id,
        user_id=user.id,
        label="Data Analyst Resume",
        duplicate_from_version_id=source.id,
    )

    assert duplicated["label"] == "Data Analyst Resume"
    assert duplicated["status_key"] == "not_analyzed"
    assert duplicated["overall_score"] is None

    dup_version = await version_repo.get_by_id(duplicated["id"])
    assert dup_version is not None
    assert dup_version.parent_version_id == source.id
    assert dup_version.content_snapshot == source.content_snapshot

    dup_analyses = await analysis_repo.list_by_resume(resume.id)
    dup_only = [a for a in dup_analyses if a.resume_version_id == duplicated["id"]]
    assert dup_only == []


@pytest.mark.asyncio
async def test_rename_version(db_session) -> None:
    resume_repo = ResumeRepository(db_session)
    version_repo = ResumeVersionRepository(db_session)
    service = VersionService(db_session)

    user = await _create_test_user(db_session)

    resume = await resume_repo.create(user_id=user.id, title="Rename", parsed_structure=SAMPLE_RESUME_PARSED)
    version = await version_repo.create(
        resume_id=resume.id,
        version_number=1,
        label="Old Label",
        content_snapshot=SAMPLE_RESUME_PARSED,
        source=ResumeVersionSource.UPLOAD,
        status=ResumeVersionStatus.ACTIVE,
    )
    await db_session.flush()

    updated = await service.rename_version(
        resume.id,
        version.id,
        user_id=user.id,
        label="AI/ML Resume",
    )
    assert updated["label"] == "AI/ML Resume"


@pytest.mark.asyncio
async def test_delete_version_cascades_related_records(db_session) -> None:
    resume_repo = ResumeRepository(db_session)
    version_repo = ResumeVersionRepository(db_session)
    analysis_repo = ResumeAnalysisRepository(db_session)
    job_repo = JobDescriptionRepository(db_session)
    service = VersionService(db_session)

    user = await _create_test_user(db_session)

    resume = await resume_repo.create(
        user_id=user.id,
        title="Delete Test",
        parsed_structure=SAMPLE_RESUME_PARSED,
    )
    keep = await version_repo.create(
        resume_id=resume.id,
        version_number=1,
        label="Keep",
        content_snapshot=SAMPLE_RESUME_PARSED,
        source=ResumeVersionSource.UPLOAD,
        status=ResumeVersionStatus.ACTIVE,
    )
    doomed = await version_repo.create(
        resume_id=resume.id,
        version_number=2,
        label="Delete Me",
        content_snapshot=SAMPLE_RESUME_PARSED,
        source=ResumeVersionSource.MANUAL,
        status=ResumeVersionStatus.ACTIVE,
        parent_version_id=keep.id,
    )
    analysis = await analysis_repo.create(
        resume_id=resume.id,
        resume_version_id=doomed.id,
        overall_score=70,
        status=AnalysisStatus.COMPLETED,
    )
    job = await job_repo.create(
        title="Engineer JD",
        raw_text="Need Python",
        parsed_requirements={"job_title": "Engineer"},
    )
    match = JobMatch(
        resume_id=resume.id,
        resume_version_id=doomed.id,
        job_description_id=job.id,
        match_score=65,
        breakdown={"summary": "test"},
    )
    db_session.add(match)
    await db_session.flush()

    recommendation = Recommendation(
        resume_id=resume.id,
        source_type=RecommendationSourceType.JOB_MATCH,
        job_match_id=match.id,
        priority=1,
        category="skill_gap",
        title="AWS",
    )
    db_session.add(recommendation)
    await db_session.flush()

    await service.delete_version(resume.id, doomed.id, user_id=user.id)

    assert await version_repo.get_by_id(doomed.id) is None
    assert await db_session.get(ResumeAnalysis, analysis.id) is None
    assert await db_session.get(JobMatch, match.id) is None
    assert await db_session.get(Recommendation, recommendation.id) is None

    remaining = await version_repo.list_by_resume(resume.id)
    assert len(remaining) == 1
    assert remaining[0].id == keep.id


@pytest.mark.asyncio
async def test_cannot_delete_last_version(db_session) -> None:
    resume_repo = ResumeRepository(db_session)
    version_repo = ResumeVersionRepository(db_session)
    service = VersionService(db_session)

    user = await _create_test_user(db_session)

    resume = await resume_repo.create(
        user_id=user.id,
        title="Last",
        parsed_structure=SAMPLE_RESUME_PARSED,
    )
    version = await version_repo.create(
        resume_id=resume.id,
        version_number=1,
        label="Only",
        content_snapshot=SAMPLE_RESUME_PARSED,
        source=ResumeVersionSource.UPLOAD,
        status=ResumeVersionStatus.ACTIVE,
    )
    await db_session.flush()

    with pytest.raises(AppError) as exc:
        await service.delete_version(resume.id, version.id, user_id=user.id)
    assert exc.value.code == "version_delete_last"


@pytest.mark.asyncio
async def test_versions_do_not_share_analysis(db_session) -> None:
    resume_repo = ResumeRepository(db_session)
    version_repo = ResumeVersionRepository(db_session)
    analysis_repo = ResumeAnalysisRepository(db_session)
    service = VersionService(db_session)

    user = await _create_test_user(db_session)

    resume = await resume_repo.create(
        user_id=user.id,
        title="Scope",
        parsed_structure=SAMPLE_RESUME_PARSED,
    )
    v1 = await version_repo.create(
        resume_id=resume.id,
        version_number=1,
        label="V1",
        content_snapshot=SAMPLE_RESUME_PARSED,
        source=ResumeVersionSource.UPLOAD,
        status=ResumeVersionStatus.ACTIVE,
    )
    v2 = await version_repo.create(
        resume_id=resume.id,
        version_number=2,
        label="V2",
        content_snapshot=SAMPLE_RESUME_PARSED,
        source=ResumeVersionSource.MANUAL,
        status=ResumeVersionStatus.ACTIVE,
    )
    await analysis_repo.create(
        resume_id=resume.id,
        resume_version_id=v1.id,
        overall_score=88,
        status=AnalysisStatus.COMPLETED,
    )
    await db_session.flush()

    versions = await service.list_versions(resume.id, user_id=user.id)
    by_id = {item["id"]: item for item in versions}
    assert by_id[v1.id]["overall_score"] == 88
    assert by_id[v2.id]["status_key"] == "not_analyzed"

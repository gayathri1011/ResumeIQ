import pytest

from app.core.database import MongoSession
from app.models.enums import AnalysisStatus, ResumeVersionSource, ResumeVersionStatus
from app.repositories import (
    ResumeAnalysisRepository,
    ResumeRepository,
    ResumeVersionRepository,
    UserRepository,
)


@pytest.mark.asyncio
async def test_user_resume_crud(db_session: MongoSession) -> None:
    user_repo = UserRepository(db_session)
    resume_repo = ResumeRepository(db_session)
    version_repo = ResumeVersionRepository(db_session)
    analysis_repo = ResumeAnalysisRepository(db_session)

    user = await user_repo.create(
        email="test@resumeiq.dev",
        password_hash="hashed-placeholder",
        full_name="Test User",
    )
    assert user.id is not None

    resume = await resume_repo.create(
        user_id=user.id,
        title="Software Engineer Resume",
        raw_text="Sample resume text",
    )
    assert resume.id is not None

    version = await version_repo.create(
        resume_id=resume.id,
        version_number=1,
        label="Original",
        raw_text="Sample resume text",
        source=ResumeVersionSource.UPLOAD,
        status=ResumeVersionStatus.ACTIVE,
    )
    assert version.id is not None

    analysis = await analysis_repo.create(
        resume_id=resume.id,
        resume_version_id=version.id,
        overall_score=78,
        category_scores={"ats": 80, "skills": 75},
        issues=[{"severity": "medium", "message": "Add metrics to bullets"}],
        status=AnalysisStatus.COMPLETED,
    )
    assert analysis.id is not None

    fetched = await resume_repo.get_by_id(resume.id)
    assert fetched is not None
    assert fetched.title == "Software Engineer Resume"

    user_resumes = await resume_repo.list_by_user(user.id)
    assert len(user_resumes) == 1

    await db_session.commit()


@pytest.mark.asyncio
async def test_mongodb_ping(db_session: MongoSession) -> None:
    from app.core.database import get_mongo_client

    result = await get_mongo_client().admin.command("ping")
    assert result.get("ok") == 1

"""Resource ownership checks for multi-user authorization."""

from __future__ import annotations

from uuid import UUID

from app.core.exceptions import AppError
from app.models.job import JobDescription
from app.models.resume import Resume
from app.repositories import JobDescriptionRepository, ResumeRepository


async def require_owned_resume(
    repo: ResumeRepository,
    resume_id: UUID,
    user_id: UUID,
) -> Resume:
    resume = await repo.get_by_id(resume_id)
    if resume is None or resume.user_id != user_id:
        raise AppError("Resume not found.", code="resume_not_found", status_code=404)
    return resume


async def require_owned_job(
    repo: JobDescriptionRepository,
    job_id: UUID,
    user_id: UUID,
) -> JobDescription:
    job = await repo.get_by_id(job_id)
    if job is None or job.user_id != user_id:
        raise AppError("Job description not found.", code="job_not_found", status_code=404)
    return job

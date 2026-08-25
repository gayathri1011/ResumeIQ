"""Helpers for creating resume versions with basic concurrency safety."""

from __future__ import annotations

import uuid
from typing import Any

from pymongo.errors import DuplicateKeyError

from app.core.database import MongoSession
from app.core.exceptions import AppError
from app.repositories import ResumeVersionRepository


async def create_resume_version(
    session: MongoSession,
    *,
    resume_id: uuid.UUID,
    max_attempts: int = 3,
    **fields: Any,
):
    version_repo = ResumeVersionRepository(session)

    for attempt in range(max_attempts):
        version_number = await version_repo.get_next_version_number(resume_id)
        try:
            return await version_repo.create(
                resume_id=resume_id,
                version_number=version_number,
                **fields,
            )
        except AppError as exc:
            if exc.code != "database_conflict" or attempt >= max_attempts - 1:
                raise
        except DuplicateKeyError as exc:
            await session.rollback()
            if attempt >= max_attempts - 1:
                raise AppError(
                    "Could not create a new resume version due to a concurrent update. Please try again.",
                    code="version_create_conflict",
                    status_code=409,
                ) from exc

    raise AppError(
        "Could not create a new resume version. Please try again.",
        code="version_create_conflict",
        status_code=409,
    )

"""Bullet improvement API schemas."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import Field

from app.schemas.common import BaseSchema


class ImproveBulletRequest(BaseSchema):
    bullet_text: str = Field(min_length=1)
    resume_id: uuid.UUID | None = None
    resume_version_id: uuid.UUID | None = None
    target_role: str | None = Field(default=None, max_length=255)
    regenerate: bool = False
    previous_improved_text: str | None = None


class ImproveBulletResponse(BaseSchema):
    original_text: str
    improved_text: str
    changes_summary: str
    metric_placeholder_used: bool = False
    suggested_metric_prompt: str | None = None
    regenerate: bool = False
    prompt_version: str


class ReplaceBulletRequest(BaseSchema):
    resume_id: uuid.UUID
    resume_version_id: uuid.UUID | None = None
    section: Literal["experience", "projects"]
    entry_index: int = Field(ge=0)
    bullet_index: int = Field(ge=0)
    improved_text: str = Field(min_length=1)


class ReplaceBulletResponse(BaseSchema):
    resume_id: uuid.UUID
    section: str
    entry_index: int
    bullet_index: int
    updated_text: str
    message: str


class ResumeBulletItem(BaseSchema):
    section: str
    entry_index: int
    bullet_index: int
    entry_title: str | None = None
    organization: str | None = None
    text: str

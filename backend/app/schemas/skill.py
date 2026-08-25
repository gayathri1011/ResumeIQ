import uuid

from pydantic import Field

from app.models.enums import ResumeSkillSource, SkillImportance, SkillProficiency
from app.schemas.common import BaseSchema, TimestampSchema


class SkillCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=255)
    normalized_name: str = Field(min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=128)


class SkillUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    normalized_name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=128)


class SkillRead(TimestampSchema):
    id: uuid.UUID
    name: str
    normalized_name: str
    category: str | None


class ResumeSkillCreate(BaseSchema):
    resume_id: uuid.UUID
    skill_id: uuid.UUID
    proficiency: SkillProficiency | None = None
    source: ResumeSkillSource = ResumeSkillSource.PARSED


class ResumeSkillRead(TimestampSchema):
    id: uuid.UUID
    resume_id: uuid.UUID
    skill_id: uuid.UUID
    proficiency: SkillProficiency | None
    source: ResumeSkillSource


class JobRequiredSkillCreate(BaseSchema):
    job_description_id: uuid.UUID
    skill_id: uuid.UUID
    importance: SkillImportance = SkillImportance.REQUIRED


class JobRequiredSkillRead(TimestampSchema):
    id: uuid.UUID
    job_description_id: uuid.UUID
    skill_id: uuid.UUID
    importance: SkillImportance

from __future__ import annotations

import uuid

from pymongo import ASCENDING, IndexModel

from app.core.database import MongoDocument
from app.models.enums import ResumeSkillSource, SkillImportance, SkillProficiency


class Skill(MongoDocument):
    name: str
    normalized_name: str
    category: str | None = None

    class Settings:
        name = "skills"
        indexes = [
            IndexModel([("normalized_name", ASCENDING)], unique=True),
            IndexModel([("category", ASCENDING)]),
        ]

    def __repr__(self) -> str:
        return f"<Skill id={self.id} name={self.name!r}>"


class ResumeSkill(MongoDocument):
    resume_id: uuid.UUID
    skill_id: uuid.UUID
    proficiency: SkillProficiency | None = None
    source: ResumeSkillSource = ResumeSkillSource.PARSED

    class Settings:
        name = "resume_skills"
        indexes = [
            IndexModel([("resume_id", ASCENDING), ("skill_id", ASCENDING)], unique=True),
        ]

    def __repr__(self) -> str:
        return f"<ResumeSkill resume_id={self.resume_id} skill_id={self.skill_id}>"


class JobRequiredSkill(MongoDocument):
    job_description_id: uuid.UUID
    skill_id: uuid.UUID
    importance: SkillImportance = SkillImportance.REQUIRED

    class Settings:
        name = "job_required_skills"
        indexes = [
            IndexModel(
                [("job_description_id", ASCENDING), ("skill_id", ASCENDING)],
                unique=True,
            ),
        ]

    def __repr__(self) -> str:
        return (
            f"<JobRequiredSkill job_id={self.job_description_id} "
            f"skill_id={self.skill_id} importance={self.importance}>"
        )

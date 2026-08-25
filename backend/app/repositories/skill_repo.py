from app.core.database import MongoSession
from app.models.skill import JobRequiredSkill, ResumeSkill, Skill
from app.repositories.base import BaseRepository


class SkillRepository(BaseRepository[Skill]):
    def __init__(self, session: MongoSession) -> None:
        super().__init__(session, Skill)

    async def get_by_normalized_name(self, normalized_name: str) -> Skill | None:
        return await Skill.find_one(Skill.normalized_name == normalized_name)


class ResumeSkillRepository(BaseRepository[ResumeSkill]):
    def __init__(self, session: MongoSession) -> None:
        super().__init__(session, ResumeSkill)


class JobRequiredSkillRepository(BaseRepository[JobRequiredSkill]):
    def __init__(self, session: MongoSession) -> None:
        super().__init__(session, JobRequiredSkill)

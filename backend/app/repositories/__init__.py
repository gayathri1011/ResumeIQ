from app.repositories.analysis_repo import (
    AIAnalysisResultRepository,
    RecommendationRepository,
    ResumeAnalysisRepository,
)
from app.repositories.base import BaseRepository
from app.repositories.job_repo import JobDescriptionRepository, JobMatchRepository
from app.repositories.resume_repo import ResumeRepository, ResumeVersionRepository
from app.repositories.skill_repo import (
    JobRequiredSkillRepository,
    ResumeSkillRepository,
    SkillRepository,
)
from app.repositories.user_repo import UserRepository

__all__ = [
    "AIAnalysisResultRepository",
    "BaseRepository",
    "JobDescriptionRepository",
    "JobMatchRepository",
    "JobRequiredSkillRepository",
    "RecommendationRepository",
    "ResumeAnalysisRepository",
    "ResumeRepository",
    "ResumeSkillRepository",
    "ResumeVersionRepository",
    "SkillRepository",
    "UserRepository",
]

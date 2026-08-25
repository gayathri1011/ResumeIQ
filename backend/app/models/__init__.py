"""Beanie MongoDB documents."""

from app.models.analysis import AIAnalysisResult, Recommendation, ResumeAnalysis
from app.models.job import JobDescription, JobMatch
from app.models.resume import Resume, ResumeVersion
from app.models.skill import JobRequiredSkill, ResumeSkill, Skill
from app.models.user import User

ALL_DOCUMENTS = [
    User,
    Resume,
    ResumeVersion,
    JobDescription,
    JobMatch,
    ResumeAnalysis,
    Recommendation,
    AIAnalysisResult,
    Skill,
    ResumeSkill,
    JobRequiredSkill,
]

__all__ = [
    "AIAnalysisResult",
    "ALL_DOCUMENTS",
    "JobDescription",
    "JobMatch",
    "JobRequiredSkill",
    "Recommendation",
    "Resume",
    "ResumeAnalysis",
    "ResumeSkill",
    "ResumeVersion",
    "Skill",
    "User",
]

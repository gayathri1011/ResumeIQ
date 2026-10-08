"""Beanie MongoDB documents."""

from app.models.analysis import AIAnalysisResult, Recommendation, ResumeAnalysis
from app.models.growth import CareerGrowthPlan
from app.models.interview import InterviewSession
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
    InterviewSession,
    CareerGrowthPlan,
]

__all__ = [
    "AIAnalysisResult",
    "ALL_DOCUMENTS",
    "CareerGrowthPlan",
    "InterviewSession",
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


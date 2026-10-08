import enum


class AnalysisStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class ResumeVersionSource(str, enum.Enum):
    UPLOAD = "upload"
    OPTIMIZATION = "optimization"
    MANUAL = "manual"
    ROLE_TRANSFORMATION = "role_transformation"


class ExperienceLevel(str, enum.Enum):
    STUDENT = "student"
    ENTRY = "entry"
    MID = "mid"
    EXPERIENCED = "experienced"


class ResumeVersionStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class RecommendationSourceType(str, enum.Enum):
    ANALYSIS = "analysis"
    JOB_MATCH = "job_match"


class SkillImportance(str, enum.Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"


class SkillProficiency(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class ResumeSkillSource(str, enum.Enum):
    PARSED = "parsed"
    INFERRED = "inferred"
    MANUAL = "manual"


class AIServiceName(str, enum.Enum):
    RESUME_ANALYZER = "resume_analyzer"
    CAREER_TRAJECTORY = "career_trajectory"
    RECRUITER_LENS = "recruiter_lens"
    JOB_ANALYZER = "job_analyzer"
    JOB_MATCHER = "job_matcher"
    RESUME_OPTIMIZER = "resume_optimizer"
    ROLE_VERSION_TRANSFORMER = "role_version_transformer"
    EMBEDDING = "embedding"
    INTERVIEW_PLANNER = "interview_planner"
    INTERVIEW_EVALUATOR = "interview_evaluator"
    INTERVIEW_REPORTER = "interview_reporter"
    CAREER_GAP_ANALYZER = "career_gap_analyzer"
    CAREER_ROADMAP_GENERATOR = "career_roadmap_generator"
    CAREER_PROJECT_RECOMMENDER = "career_project_recommender"


class AIResultType(str, enum.Enum):
    ISSUES = "issues"
    SUGGESTIONS = "suggestions"
    FULL_REPORT = "full_report"
    CAREER_TRAJECTORY = "career_trajectory"
    RECRUITER_LENS = "recruiter_lens"
    JD_EXTRACTION = "jd_extraction"
    MATCH_DETAILS = "match_details"
    OPTIMIZATION = "optimization"
    ROLE_TRANSFORMATION = "role_transformation"
    INTERVIEW_PLAN = "interview_plan"
    INTERVIEW_EVALUATION = "interview_evaluation"
    INTERVIEW_REPORT = "interview_report"
    CAREER_GROWTH_PLAN = "career_growth_plan"
    CAREER_ROADMAP = "career_roadmap"
    PROJECT_RECOMMENDATIONS = "project_recommendations"


class InterviewStatus(str, enum.Enum):
    SETUP = "setup"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class GrowthPlanStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    COMPLETED = "completed"


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
    JOB_ANALYZER = "job_analyzer"
    JOB_MATCHER = "job_matcher"
    RESUME_OPTIMIZER = "resume_optimizer"
    ROLE_VERSION_TRANSFORMER = "role_version_transformer"
    BULLET_IMPROVER = "bullet_improver"
    EMBEDDING = "embedding"


class AIResultType(str, enum.Enum):
    ISSUES = "issues"
    SUGGESTIONS = "suggestions"
    FULL_REPORT = "full_report"
    JD_EXTRACTION = "jd_extraction"
    MATCH_DETAILS = "match_details"
    OPTIMIZATION = "optimization"
    ROLE_TRANSFORMATION = "role_transformation"
    BULLET_IMPROVEMENT = "bullet_improvement"

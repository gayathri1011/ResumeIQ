# ResumeIQ Extension Plan: Adaptive AI Interviewer & Career Growth Engine

**Project:** ResumeIQ 1.x Intelligence Extension  
**Phases:** Phase 1 (Inspection, Plan & Shared Backend Foundation) | Phase 2 (Adaptive AI Interviewer) | Phase 3 (Career Growth Engine & Feedback Loop)  
**Author:** Senior Software Architect + AI Product Engineer  
**Status:** Approved for Phase 1 Implementation  

---

## 1. Repository Findings & Baseline Architecture

### 1.1 Architecture & Stack Summary
- **Frontend:** Next.js 15.1 (App Router), React 19, TypeScript 5.7, Tailwind CSS 3.4 with custom editorial design tokens (`globals.css`), Framer Motion 11.15, Lucide React, Recharts 2.15, Vitest 2.1.8. Deployed to Vercel.
- **Backend:** FastAPI, Python 3.12, Uvicorn, Pydantic v2 (`BaseSchema` with `from_attributes=True`), Beanie ODM + Motor (async MongoDB client). Deployed to Render.
- **Database:** MongoDB 7.0 via Motor + Beanie. Documents inherit from `MongoDocument` (`app/core/database.py`) providing a UUID primary key (`id: uuid.UUID = Field(default_factory=uuid.uuid4)`), `created_at`, and `updated_at`. Beanie registers documents at startup via `init_beanie(database=..., document_models=ALL_DOCUMENTS)`. Note: `alembic/` is an unused legacy artifact from a previous SQL setup; all schema and index lifecycle management is handled via Beanie.
- **Authentication:** Stateless JWT bearer tokens (`app/core/security.py`). Token stored in browser `sessionStorage` (`frontend/lib/auth-storage.ts`). Frontend `apiClient` (`frontend/lib/api-client.ts`) attaches `Authorization: Bearer <token>`. FastAPI routes consume `CurrentUserDep = Annotated[User, Depends(get_current_user)]` from `app/api/deps.py`.
- **API Surface & Base Path:** Backend mounts all routers under prefix `/api/v1` via `api_v1_router` (`app/api/v1/router.py`). Frontend `NEXT_PUBLIC_API_BASE_URL` points to the host origin (e.g. `http://localhost:8000` or Render URL); client service modules prepend `/api/v1`.
- **Error Standard:** Standard JSON error envelope defined in `app/core/exceptions.py`:
  ```json
  {
    "error": {
      "code": "string_identifier",
      "message": "Human readable user-safe message",
      "details": null
    }
  }
  ```
  Client-side `api-client.ts` maps this into `ApiClientError`.
- **AI Infrastructure:** `AIService` (`app/ai/client.py`) provides structured JSON completions via `complete_structured`. Prompts are stored in YAML files (`app/ai/prompts/<task_name>_v1.yaml`) containing `system` and `user_template` blocks loaded via `app/ai/prompts/loader.py`. Task classes format user prompt templates, pass a Pydantic schema to `complete_structured`, store raw execution artifacts in `AIAnalysisResult` (`ai_analysis_results` collection), and compute deterministic domain metrics.

---

## 2. Existing Components, Models, Services & Routes to Reuse

| Component / Layer | Exact File Path | Reusability in Interviewer & Career Engine |
|---|---|---|
| **Database Document Base** | `backend/app/core/database.py` | `MongoDocument`, `MongoSession`, UUID generation, timestamp hooks. |
| **Auth Dependencies** | `backend/app/api/deps.py` | `CurrentUserDep`, `AsyncSessionDep`, bearer token decoding. |
| **Error Handlers** | `backend/app/core/exceptions.py` | `AppError`, `build_error_response`, rate-limit error classes. |
| **Existing Document Models** | `backend/app/models/resume.py`<br>`backend/app/models/job.py`<br>`backend/app/models/analysis.py` | `Resume`, `ResumeVersion`, `JobDescription`, `JobMatch`, `ResumeAnalysis`, `AIAnalysisResult`. |
| **Existing Repositories** | `backend/app/repositories/*.py` | `ResumeRepository`, `ResumeVersionRepository`, `JobDescriptionRepository`, `JobMatchRepository`, `ResumeAnalysisRepository`, `AIAnalysisResultRepository`. |
| **Ownership Enforcers** | `backend/app/utils/ownership.py` | `require_owned_resume`, `require_owned_job`. |
| **Prompt Loader** | `backend/app/ai/prompts/loader.py` | `load_prompt(name: str)` for YAML templates. |
| **Career Trajectory Analyzer** | `backend/app/ai/tasks/career_trajectory.py` | Role adjacency extraction, skill and proof gap definitions, readiness factor heuristics. |
| **Skill Gap Analyzer** | `backend/app/ai/tasks/skill_gap_analyzer.py` | Prioritized missing skill calculations, coverage formula weights (1.0 required, 0.5 preferred). |
| **Frontend Layout & Nav** | `frontend/components/layout/AppShell.tsx` | Main navigation shell, responsive drawer, active pill animations. |
| **Frontend UI Primitives** | `frontend/components/ui/*.tsx` | `Button`, `Card`, `Badge`, `Alert`, `Tabs`, `Dialog`, `FeatureSkeleton`. |
| **Frontend Score Display** | `frontend/features/dashboard/CircularScore.tsx` | Circular SVG score gauge matching ResumeIQ branding. |
| **Frontend API Client** | `frontend/lib/api-client.ts` | Authenticated fetch wrapper, error parser, 401 redirect handling. |

---

## 3. Existing Files Requiring Modification (Minimal & Additive)

1. `backend/app/models/__init__.py`:
   - *Reason:* Register new Beanie document models (`InterviewSession`, `CareerGrowthPlan`) in `ALL_DOCUMENTS` and `__all__` so MongoDB creates collections and indexes at application startup.
2. `backend/app/models/enums.py`:
   - *Reason:* Add new enum values for `AIServiceName` (`INTERVIEW_PLANNER`, `INTERVIEW_EVALUATOR`, `INTERVIEW_REPORTER`, `CAREER_GAP_ANALYZER`, `CAREER_ROADMAP_GENERATOR`, `CAREER_PROJECT_RECOMMENDER`) and `AIResultType` (`INTERVIEW_PLAN`, `INTERVIEW_EVALUATION`, `INTERVIEW_REPORT`, `CAREER_GROWTH_PLAN`, `CAREER_ROADMAP`, `PROJECT_RECOMMENDATIONS`), plus `InterviewStatus` and `GrowthPlanStatus`.
3. `backend/app/ai/providers/mock_provider.py`:
   - *Reason:* Add mock prompt resolvers for the six new task prompts so local development and automated pytest test suites function deterministically with `AI_MOCK_MODE=true`.
4. `backend/app/repositories/__init__.py`:
   - *Reason:* Export new repositories (`InterviewSessionRepository`, `CareerGrowthPlanRepository`).
5. *(Deferred to Phase 2/3)* `backend/app/api/v1/router.py`:
   - *Reason:* Mount `/interviews` and `/growth` routers when endpoints are implemented.
6. *(Deferred to Phase 2/3)* `frontend/components/layout/AppShell.tsx`:
   - *Reason:* Add "Interview" and "Career Growth" links to the global navigation bar.

---

## 4. New Files Required (Phase 1 Shared Foundation)

### Models & Repositories
- `backend/app/models/interview.py`: `InterviewSession`, `InterviewTurn`, `InterviewQuestionRubric` embedded documents and settings.
- `backend/app/models/growth.py`: `CareerGrowthPlan`, `SkillGapRecord`, `RoadmapPhaseRecord`, `ProjectRecommendationRecord`, `EvidenceEvent` documents and settings.
- `backend/app/repositories/interview_repository.py`: CRUD and query methods for `InterviewSession`.
- `backend/app/repositories/growth_repository.py`: CRUD and query methods for `CareerGrowthPlan`.

### Typed AI Output Schemas
- `backend/app/ai/schemas/interview_output.py`:
  - `InterviewPlanOutput`
  - `InterviewTurnEvalOutput`
  - `InterviewReportOutput`
- `backend/app/ai/schemas/growth_output.py`:
  - `CareerSkillGapOutput`
  - `CareerRoadmapOutput`
  - `ProjectRecommendationsOutput`

### YAML Prompts
- `backend/app/ai/prompts/interview_plan_v1.yaml`
- `backend/app/ai/prompts/interview_turn_eval_v1.yaml`
- `backend/app/ai/prompts/interview_report_v1.yaml`
- `backend/app/ai/prompts/career_skill_gap_v1.yaml`
- `backend/app/ai/prompts/career_roadmap_v1.yaml`
- `backend/app/ai/prompts/career_project_recommendations_v1.yaml`

### AI Infrastructure Extensions & Candidate Profile Builder
- `backend/app/ai/safe_client.py`: `RobustAIService` wrapper providing timeout protection, empty response safeguards, single bounded repair/retry, deterministic fallback factories, and server-side sanitized error logging.
- `backend/app/ai/fallbacks.py`: Deterministic fallback generators for all six AI tasks.
- `backend/app/services/profile_builder.py`: `CandidateProfileBuilder` assembling compact, sanitized candidate profile summaries from existing stored records (`Resume`, `ResumeAnalysis`, `JobMatch`, `CareerTrajectory`, `RecruiterLens`) without triggering expensive AI re-runs.

### Unit Tests
- `backend/tests/test_ai_foundation.py`: Verification tests covering schema validation, malformed output fallback triggers, safe client timeout behavior, and candidate profile builder assembling against mock data.

---

## 5. Database Additions (Models, Fields & Indexes)

### 5.1 Collection: `interview_sessions` (`InterviewSession`)
```python
class InterviewTurn(BaseModel):
    turn_index: int
    question: str
    skill_tag: str
    question_type: str  # "technical" | "behavioral" | "system_design" | "problem_solving"
    difficulty: str     # "junior" | "mid" | "senior" | "staff"
    expected_criteria: list[str] = []
    user_answer: str | None = None
    answered_at: datetime | None = None
    turn_score: int | None = None  # 0-100
    strengths: list[str] = []
    areas_for_improvement: list[str] = []
    criteria_feedback: list[dict[str, Any]] = []
    next_action: str | None = None # "follow_up" | "next_topic" | "wrap_up"
    interviewer_notes: str | None = None

class InterviewSession(MongoDocument):
    user_id: uuid.UUID
    resume_id: uuid.UUID | None = None
    resume_version_id: uuid.UUID | None = None
    job_description_id: uuid.UUID | None = None
    target_role: str
    difficulty: str = "mid"
    status: InterviewStatus = InterviewStatus.SETUP
    plan: dict[str, Any] | None = None
    turns: list[InterviewTurn] = []
    current_turn_index: int = 0
    report: dict[str, Any] | None = None
    overall_score: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    class Settings:
        name = "interview_sessions"
        indexes = [
            IndexModel([("user_id", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("resume_id", ASCENDING)]),
            IndexModel([("job_description_id", ASCENDING)]),
        ]
```

### 5.2 Collection: `career_growth_plans` (`CareerGrowthPlan`)
```python
class SkillGapRecord(BaseModel):
    skill: str
    priority: str          # "high" | "medium" | "low"
    gap_type: str          # "missing_capability" | "proof_gap"
    why_it_matters: str
    target_competency: str
    verified_in_interview: bool = False
    latest_interview_score: int | None = None
    evidence_count: int = 0

class RoadmapMilestone(BaseModel):
    milestone_id: str
    title: str
    skills_addressed: list[str] = []
    status: str = "not_started" # "not_started" | "in_progress" | "completed"
    completed_at: datetime | None = None

class RoadmapPhaseRecord(BaseModel):
    phase_number: int
    name: str
    duration_weeks: int
    focus_skills: list[str] = []
    milestones: list[RoadmapMilestone] = []

class ProjectRecommendationRecord(BaseModel):
    project_id: str
    title: str
    description: str
    targeted_skills: list[str] = []
    difficulty: str
    architecture_overview: str
    key_deliverables: list[str] = []
    resume_bullet_preview: str

class EvidenceEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_type: str       # "interview" | "project_submission" | "manual"
    source_id: str         # e.g. interview_session_id
    idempotency_key: str   # e.g. "interview:<session_id>:<skill>"
    skill: str
    score: int
    notes: str
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class CareerGrowthPlan(MongoDocument):
    user_id: uuid.UUID
    resume_id: uuid.UUID | None = None
    resume_version_id: uuid.UUID | None = None
    target_role: str
    target_company: str | None = None
    readiness_score: int = 0  # 0-100 deterministic
    status: GrowthPlanStatus = GrowthPlanStatus.ACTIVE
    summary: str | None = None
    skill_gaps: list[SkillGapRecord] = []
    roadmap_phases: list[RoadmapPhaseRecord] = []
    project_recommendations: list[ProjectRecommendationRecord] = []
    evidence_events: list[EvidenceEvent] = []
    last_evaluated_at: datetime | None = None

    class Settings:
        name = "career_growth_plans"
        indexes = [
            IndexModel([("user_id", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("user_id", ASCENDING), ("target_role", ASCENDING)]),
        ]
```

---

## 6. API Design for Both Features (To Be Implemented in Phase 2 & 3)

All endpoints require `Authorization: Bearer <token>` and enforce user record ownership.

### Adaptive AI Interviewer Endpoints (`/api/v1/interviews`)
1. `POST /api/v1/interviews/sessions`
   - **Request:** `{ "resume_id": UUID, "target_role": str, "job_description_id": UUID | null, "difficulty": "junior"|"mid"|"senior"|"staff", "focus_areas": string[] }`
   - **Response:** `InterviewSessionResponse` (201 Created with initial plan and first turn question)
2. `GET /api/v1/interviews/sessions`
   - **Query:** `skip=0&limit=20`
   - **Response:** `list[InterviewSessionListItem]` (200 OK)
3. `GET /api/v1/interviews/sessions/{session_id}`
   - **Response:** `InterviewSessionDetailResponse` (200 OK with turns, current state, active question)
4. `POST /api/v1/interviews/sessions/{session_id}/turns/{turn_index}/answer`
   - **Request:** `{ "answer": str }` (validated length: 10 - 5000 chars)
   - **Response:** `TurnEvaluationResponse` (evaluation of answer, score, feedback, next question or completion indicator)
5. `POST /api/v1/interviews/sessions/{session_id}/conclude`
   - **Request:** None
   - **Response:** `InterviewReportResponse` (final synthesized score, breakdown, verified strengths/gaps)

### Career Growth Engine Endpoints (`/api/v1/growth`)
1. `POST /api/v1/growth/plans`
   - **Request:** `{ "resume_id": UUID, "target_role": str, "target_company": str | null }`
   - **Response:** `CareerGrowthPlanResponse` (generates gaps, roadmap, and project recommendations)
2. `GET /api/v1/growth/plans/latest`
   - **Query:** `resume_id=UUID | null`
   - **Response:** `CareerGrowthPlanResponse` (200 OK)
3. `GET /api/v1/growth/plans/{plan_id}`
   - **Response:** `CareerGrowthPlanResponse` (200 OK)
4. `POST /api/v1/growth/plans/{plan_id}/sync-interview/{session_id}`
   - **Request:** None (idempotent evidence ingestion)
   - **Response:** `SyncInterviewResultResponse` (evidence events logged, updated readiness score, updated gaps)
5. `PATCH /api/v1/growth/plans/{plan_id}/milestones/{milestone_id}`
   - **Request:** `{ "status": "not_started"|"in_progress"|"completed" }`
   - **Response:** `CareerGrowthPlanResponse`

---

## 7. Frontend Design (Planned for Phase 2 & 3)

### Routes
- `/interview`: Active interview hub. Displays active session, role/difficulty selection, live turn-by-turn dialogue, question cards, criteria indicators, timer, transcript history, and final report card.
- `/growth`: Career Growth dashboard. Interactive readiness gauge, prioritized skill gap cards (with "Practice in Interview" quick action), interactive phased milestone roadmap, portfolio project briefs with copyable resume bullet templates, and verified evidence log.

### Design System Integration
- Preserves the established ResumeIQ aesthetic: warm sand background (`hsl(36 48% 90%)`), ink typography (`hsl(var(--ink))`), Fraunces serif headings (`--font-display`), card lift shadows, and rounded pill tags.
- Reuses `CircularScore`, `Card`, `Button`, `Badge`, `Alert`, and Lucide icons.

---

## 8. AI Design: Six Specialized Tasks & Prompts

### Untrusted Input & Prompt Injection Resistance
All prompts adhere strictly to security guidelines:
1. Candidate answers, resume text, and job descriptions are delimited using XML-style tags (`<candidate_profile>`, `<candidate_answer>`, `<job_context>`).
2. Explicit system instructions mandate ignoring embedded instructions or roleplay prompts inside untrusted tags.
3. User text is capped (answers <= 5,000 characters; resume profile <= 3,000 characters).
4. No request or storage of internal chain-of-thought; prompts require concise, coaching-focused rationales.

### Six Tasks Summary:
1. `interview_plan_v1.yaml`: Derives a structured 4-6 question progression from candidate profile and career gap.
2. `interview_turn_eval_v1.yaml`: Evaluates a single answer, scores competencies, provides strengths/improvements, and decides next adaptive question.
3. `interview_report_v1.yaml`: Synthesizes entire interview history into comprehensive scores, verified competencies, and hiring readiness level.
4. `career_skill_gap_v1.yaml`: Evaluates target role against candidate profile, producing prioritized missing skills vs proof gaps.
5. `career_roadmap_v1.yaml`: Generates a phased 30-60-90 day milestone roadmap tailored to candidate's verified status.
6. `career_project_recommendations_v1.yaml`: Generates high-impact portfolio projects designed to demonstrate proof for target skills.

---

## 9. Feedback Loop Architecture

```text
┌────────────────────────────────────────────────────────┐
│               Career Growth Plan                       │
│  - Target Role: Senior Backend Engineer                │
│  - Skill Gaps: System Design (High), Docker (Med)      │
│  - Readiness: 58%                                      │
└──────────────────────────┬─────────────────────────────┘
                           │ 1. User clicks "Practice in Interview"
                           ▼
┌────────────────────────────────────────────────────────┐
│               Adaptive AI Interviewer                  │
│  - Focus: System Design & Microservices                │
│  - Turns evaluated per skill tag                       │
└──────────────────────────┬─────────────────────────────┘
                           │ 2. Interview Concludes
                           │    (Score: System Design = 82%)
                           ▼
┌────────────────────────────────────────────────────────┐
│               Evidence Ingestion Engine                │
│  - Idempotency Key: `interview:{session_id}:{skill}`   │
│  - Append EvidenceEvent to Growth Plan                 │
│  - Update SkillGap: System Design -> Verified (82%)    │
│  - Recompute Readiness: 58% -> 72%                     │
│  - Auto-advance associated Roadmap Milestones          │
└────────────────────────────────────────────────────────┘
```

**Idempotency & Recomputation:**
- Ingestion creates `EvidenceEvent` records keyed by `interview:<session_id>:<skill>`. Duplicate sync requests safely exit with 200 OK without re-applying scores.
- Readiness recomputation is deterministic:
  $$\text{Readiness} = \sum (\text{Skill Weight} \times \text{Competency Score})$$
  Ensuring transparent, explainable scores aligned with ResumeIQ principles.

---

## 10. Risks & Regression Avoidance Strategy

1. **Zero Regression on Existing Routes:**
   - No modifications to existing resume upload, analysis, job match, career trajectory, or recruiter lens endpoints.
   - All additions are strictly additive.
2. **AI Rate Limiting & Timeouts:**
   - Provider timeouts capped at 45 seconds with deterministic fallbacks to prevent hanging connections.
   - Bounded single retry on malformed JSON; raw provider errors logged internally and never returned to client.
3. **Database Performance:**
   - Explicit compound indexes created on `(user_id, status)` and `(user_id, created_at)` for both collections to ensure O(1) query performance.

---

## 11. Test Strategy

1. **Unit Tests (Phase 1):**
   - Test all 6 Pydantic AI output schemas against valid and malformed payloads.
   - Test `RobustAIService` fallback handling when provider outputs empty or invalid JSON.
   - Test `CandidateProfileBuilder` assembling compact profiles across complete, partial, and empty resume records.
2. **Regression Check:**
   - Verify existing test suite runs and passes without disruption.

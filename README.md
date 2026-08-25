# ResumeIQ

> AI Resume Intelligence & Job Matching Platform

ResumeIQ is a full-stack SaaS application that helps job seekers understand how their resume performs, how well it matches a target role, and what to improve — with explainable AI, version history, and grounded safeguards against fabricated content.

---

## Project Overview

Job seekers often lack feedback on **why** an ATS might score their resume poorly, which keywords or skills are missing for a role, and how to improve bullets without inventing experience. ResumeIQ solves this by:

1. Parsing uploaded PDF/DOCX resumes into a structured schema
2. Running AI-powered resume health analysis with per-dimension scores and “Why this score?” explainability
3. Analyzing pasted job descriptions and matching them semantically + structurally against the resume
4. Surfacing skill/keyword gaps and actionable improvement paths
5. Letting users improve individual bullets, run role-targeted optimization with accept/reject review, and export a polished PDF

Every AI feature is tied to **actual resume/JD content** — the system validates outputs and rejects hallucinated metrics or invented employers/dates.

---

## Features (as built)

| Area | Capability |
|------|------------|
| **Auth** | Email/password signup, login, JWT access tokens, logout, `/me` profile |
| **Resume upload** | PDF & DOCX upload, validation, structured extraction, version `Original Upload` |
| **Dashboard** | Resume health score, category breakdown chart, job match summary, staleness warnings |
| **AI analysis** | Overall + category scores, issues, dimension explanations, content-hash cache reuse |
| **ATS-style scoring** | Structured rubric dimensions (formatting, keywords, impact, etc.) with grounded issue lists |
| **Job descriptions** | Paste JD text → AI extraction of title, skills, responsibilities, keywords |
| **Job matching** | Semantic embedding similarity + AI breakdown (skills, experience, keywords, projects, education) |
| **Skill gap** | Missing skills/keywords, learning roadmap; recommendations persisted to DB |
| **Bullet improver** | Single-bullet rewrite with metric-fabrication checks |
| **Optimization** | Role- or JD-grounded full-resume optimization with per-change accept/reject |
| **Before/after** | Section-by-section comparison in optimization review |
| **Versions** | List, duplicate, upload new version, analyze/optimize per version, delete |
| **PDF export** | Generate downloadable PDF from any version via Jinja2 + WeasyPrint-style HTML pipeline |
| **Security** | Per-user ownership checks, rate limits on auth/AI, no API keys in frontend |

### Explicitly out of scope / deferred

- Standalone **Recommendations API/UI** (data is stored during skill-gap analysis but not exposed as its own screen)
- **Email verification** and **refresh tokens**
- **Background job queue** (AI/PDF run inline in request handlers; blocking file/PDF work offloaded to thread pool)
- **Multiple resume PDF templates**
- **Normalized Skills table** (schema exists; matching uses AI + embeddings, not the lookup table)
- **S3 file storage** (local filesystem backend only)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Next.js 15 frontend (App Router, TypeScript, Tailwind/shadcn) │
│  JWT in memory/localStorage · api-client · feature modules      │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS /api/v1/*
┌────────────────────────────▼────────────────────────────────────┐
│  FastAPI backend                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ API routes  │→ │ Services     │→ │ Repositories (Beanie)   │ │
│  └─────────────┘  └──────┬───────┘  └───────────┬─────────────┘ │
│                          │                       │               │
│                   ┌──────▼───────┐        ┌──────▼──────┐        │
│                   │ AI tasks     │        │ MongoDB     │        │
│                   │  matcher,    │        └─────────────┘        │
│                   │  optimizer,  │                               │
│                   │  bullets)    │        ┌─────────────┐        │
│                   └──────┬───────┘        │ Local file  │        │
│                          │                │ uploads     │        │
│                   ┌──────▼───────┐        └─────────────┘        │
│                   │ AIService    │                               │
│                   │ (Groq /      │                               │
│                   │  mock mode)  │                               │
│                   └──────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

**Monorepo layout**

- `backend/` — FastAPI app, Beanie models, pytest suite
- `frontend/` — Next.js app, Vitest unit tests
- `docker-compose.yml` — MongoDB 7

---

## Tech Stack

| Layer | Technologies |
|-------|--------------|
| **Frontend** | Next.js 15, React 19, TypeScript, Tailwind CSS, shadcn-style UI primitives, Framer Motion, Recharts (lazy-loaded on dashboard) |
| **Backend** | FastAPI, Pydantic v2, Beanie 1.26 + Motor |
| **Database** | MongoDB 7 (Beanie ODM + Motor). Embeddings stored as float arrays; cosine similarity is computed in application code. |
| **AI** | Groq (`openai/gpt-oss-120b` chat; local embedding fallback when Groq embed API unavailable); mock provider for tests. OpenAI remains optional via `AI_PROVIDER=openai`. |
| **Parsing** | PyMuPDF (PDF), python-docx (DOCX) |
| **PDF generation** | Jinja2 HTML template → PyMuPDF `Story` renderer (`app/pdf/`) |
| **Auth** | bcrypt password hashing, PyJWT access tokens |

---

## System Workflow

1. **Register / login** → receive JWT access token
2. **Upload resume** (PDF/DOCX) → parse → store `resumes` + `resume_versions` (v1) → optional embedding
3. **Dashboard** → select resume/version → view scores or run **Analyze**
4. **Job analyzer** → paste JD → AI extracts requirements → store `job_descriptions`
5. **Match** → link resume version to JD → combined semantic + structured match score
6. **Skill gap** → missing skills/keywords + roadmap (recommendations saved internally)
7. **Bullet improver** → pick a bullet → AI rewrite → **Replace** updates version content
8. **Optimize** → target role (+ optional JD) → review changes → accept/reject → apply to version
9. **Versions** → duplicate, compare status, re-analyze when stale
10. **Generate PDF** → download current version

**Staleness:** When content changes (bullet replace, optimization apply), `_meta.content_updated_at` is updated and analysis/match records are compared by content hash — dashboard shows “re-analyze recommended” without over-invalidating unchanged content.

---

## AI Workflow

### AIService abstraction (`backend/app/ai/client.py`)

- Single entry point: `complete_structured()` with Pydantic output schemas, retries, timeouts
- Providers: **Groq** (default) or **Mock** (`AI_MOCK_MODE=true`). OpenAI is still available if `AI_PROVIDER=openai`.
- Token usage and prompt versions persisted on `ai_analysis_results`

### Task modules (consumers)

| Task | File | Purpose |
|------|------|---------|
| ResumeAnalyzer | `ai/tasks/resume_analyzer.py` | Health/ATS-style scores + issues |
| JobDescriptionAnalyzer | `ai/tasks/job_analyzer.py` | JD structuring |
| JobMatcher | `ai/tasks/job_matcher.py` | Match score + breakdown |
| SkillGapAnalyzer | `ai/tasks/skill_gap_analyzer.py` | Gaps + roadmap |
| ResumeOptimizer | `ai/tasks/resume_optimizer.py` | Full resume optimization |
| BulletPointImprover | `ai/tasks/bullet_improver.py` | Single bullet rewrite |

### Why AI?

Structured parsing alone cannot judge writing quality, role fit, or nuanced ATS heuristics. LLMs evaluate narrative clarity, impact language, and role alignment — but only when constrained by schemas, prompts, and post-validation.

### Why embeddings?

Resume and JD text are embedded (`nomic-embed-text-v1_5` on Groq, 768 dimensions) and stored on the resume/JD documents in MongoDB. **Semantic similarity** (cosine) contributes **30%** of the job match score (`SEMANTIC_WEIGHT` in `job_matcher.py`), complementing structured skill/keyword matching from the AI breakdown.

### How ATS scoring works

`ResumeAnalyzer` prompts the model with the structured resume JSON and asks for:

- `overall_score` (0–100)
- Per-category scores (formatting, keywords, impact, etc.)
- `issues[]` with severity, grounded explanations, and suggested fixes
- Dimension-level “why” text surfaced in the **Why this score?** dialog

Scores are **heuristic assessments**, not guarantees of real ATS vendor behavior — disclaimers are included in dimension output.

### How job matching works

1. Ensure resume + JD embeddings exist (`EmbeddingService`)
2. Compute cosine similarity → `semantic_score`
3. Hash `(resume_content_hash, job_text_hash, version_id)` — reuse cached AI match if unchanged
4. AI produces breakdown subscores: skills, experience, keywords, projects, education
5. Weighted blend: `semantic * 0.30 + breakdown_weighted * 0.70`
6. Persist `job_matches` with matched/missing skills and keyword lists

### Anti-fabrication safeguards

| Layer | Mechanism |
|-------|-----------|
| **Prompts** | Explicit “do not invent employers, dates, degrees, or metrics” |
| **Bullet improver** | `find_fabricated_metrics()` rejects new numbers not in source bullet/context |
| **Optimizer** | `validate_structural_facts_preserved()`, `validate_no_fabricated_content()`, grounded change explanations |
| **Analysis issues** | `grounded_in_resume` flag; issues tied to parsed content |
| **Caching** | Content-hash keys — same bytes → same result; content edits → new hash → re-analysis |

---

## Database Architecture

Core collections (Beanie documents in MongoDB):

| Collection | Role |
|-------|------|
| `users` | Accounts |
| `resumes` | Canonical resume record + parsed JSON + embedding |
| `resume_versions` | Immutable-ish snapshots per version; optimization drafts |
| `resume_analyses` | Analysis runs linked to resume/version |
| `job_descriptions` | Raw JD text + parsed requirements + embedding |
| `job_matches` | Match results, scores, breakdown JSON |
| `ai_analysis_results` | Deduplicated AI payloads keyed by `input_hash` + `service_name` |
| `recommendations` | Skill-gap suggestions (no public list API yet) |
| `skills` | Reference table (unused in runtime matching) |

**Indexes:** `user_id`, `resume_id`, `resume_version_id`, unique `(resume_id, version_number)`, unique `email`, `(input_hash, service_name)` on `ai_analysis_results`. Embeddings are float arrays on documents (cosine similarity in Python, not Atlas Vector Search).

**Relationships:** User → many Resumes → many Versions; Resume + JD → JobMatch; Analysis/AI results optionally link to version and JD.

---

## API Documentation

Base URL: `http://localhost:8000/api/v1`  
Auth: `Authorization: Bearer <access_token>` on protected routes  
Interactive docs: `http://localhost:8000/api/docs`

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | `{ "status": "ok" }` |

### Auth

| Method | Path | Body | Response |
|--------|------|------|----------|
| POST | `/auth/signup` | `{ email, password, full_name? }` | `{ access_token, token_type, user }` |
| POST | `/auth/login` | `{ email, password }` | same |
| POST | `/auth/logout` | — | `{ message }` |
| GET | `/auth/me` | — | `UserRead` |

### Resumes

| Method | Path | Notes |
|--------|------|-------|
| GET | `/resumes?limit=50&offset=0` | Paginated dashboard list |
| POST | `/resumes/upload` | `multipart/form-data` file |
| GET | `/resumes/{id}?versionId=` | Detail + latest analysis/match |
| POST | `/resumes/{id}/analyze?versionId=` | Rate-limited AI analysis |
| GET | `/resumes/{id}/matches?versionId=&limit=&offset=` | Paginated match history |
| GET | `/resumes/{id}/skill-gap?jobDescriptionId=&versionId=` | Skill gap for a JD |
| POST | `/resumes/{id}/optimize` | Body: `{ target_role, job_description_id?, resume_version_id? }` |
| GET | `/resumes/{id}/optimization/latest?versionId=` | Latest proposal or null |
| POST | `/resumes/{id}/optimization/apply` | Body: `{ optimization_id, decisions[], resume_version_id? }` |
| GET | `/resumes/{id}/versions?limit=&offset=` | Paginated versions |
| POST | `/resumes/{id}/versions` | Form: label, optional duplicate/upload |
| PATCH | `/resumes/{id}/versions/{versionId}` | Update label/status |
| DELETE | `/resumes/{id}/versions/{versionId}` | Delete version |
| POST | `/resumes/{id}/versions/{versionId}/analyze` | Version-scoped analyze |
| POST | `/resumes/{id}/versions/{versionId}/optimize` | Version-scoped optimize |
| POST | `/resumes/{id}/versions/{versionId}/generate` | Returns PDF stream |

### Jobs

| Method | Path | Notes |
|--------|------|-------|
| GET | `/jobs?limit=&offset=` | Paginated JD list |
| POST | `/jobs/analyze` | Body: `{ raw_text, company?, resume_id?, resume_version_id? }` |
| GET | `/jobs/{id}` | JD detail |
| POST | `/jobs/{id}/match` | Body: `{ resume_id, resume_version_id? }` |
| GET | `/jobs/{id}/skill-gap?resume_id=&resume_version_id=` | Skill gap from JD side |

### Bullets

| Method | Path | Notes |
|--------|------|-------|
| POST | `/bullets/improve` | Body: `{ bullet_text, resume_id?, resume_version_id?, target_role? }` |
| POST | `/bullets/replace` | Body: `{ resume_id, section, entry_index, bullet_index, improved_text, resume_version_id? }` |
| GET | `/bullets/resume/{resume_id}?versionId=` | List bullets for picker UI |

### Common error envelope

```json
{
  "error": {
    "code": "machine_readable_code",
    "message": "Human-readable message",
    "details": {}
  }
}
```

---

## Installation

### Prerequisites

- Docker Desktop (for MongoDB)
- Python 3.11+
- Node.js 20+
- Groq API key from [console.groq.com/keys](https://console.groq.com/keys) (or use `AI_MOCK_MODE=true` for local dev without AI spend)

### 1. Clone and start database

```powershell
git clone <your-repo-url> resume
cd resume
docker compose up -d
```

### 2. Backend setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
# Edit .env — set SECRET_KEY, JWT_SECRET_KEY, AI_API_KEY (or AI_MOCK_MODE=true)
```

### 3. Frontend setup

```powershell
cd ..\frontend
npm install
copy .env.local.example .env.local
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `ENVIRONMENT` | `development` / `production` |
| `DEBUG` | Enable debug logging |
| `SECRET_KEY` | App secret (sessions/internal) |
| `MONGODB_URL` | MongoDB connection string, e.g. `mongodb://localhost:27017` |
| `MONGODB_DB` | Database name (`resumeiq`) |
| `EMBEDDING_DIMENSIONS` | Vector size (`768` for Groq `nomic-embed-text-v1_5`) |
| `CORS_ORIGINS` | Comma-separated frontend origins |
| `JWT_SECRET_KEY` / `JWT_ALGORITHM` / `ACCESS_TOKEN_EXPIRE_MINUTES` | Auth |
| `AUTH_RATE_LIMIT_PER_MINUTE` | Login/signup throttle |
| `AI_RATE_LIMIT_PER_MINUTE` | Analyze/match/optimize throttle |
| `AI_PROVIDER` | `groq` (default). Use `openai` only if you switch providers. |
| `AI_API_KEY` | Groq key from console.groq.com (**server only — never expose to frontend**) |
| `AI_BASE_URL` | Groq OpenAI-compatible endpoint: `https://api.groq.com/openai/v1` |
| `AI_MODEL` | e.g. `openai/gpt-oss-120b` |
| `AI_EMBEDDING_MODEL` | e.g. `nomic-embed-text-v1_5` |
| `AI_MOCK_MODE` | `true` = deterministic mock AI for tests/dev |
| `UPLOAD_MAX_SIZE_MB` / `UPLOAD_ALLOWED_EXTENSIONS` | Upload limits |
| `FILE_STORAGE_BACKEND` | `local` |
| `FILE_STORAGE_PATH` | Upload directory |

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_BASE_URL` | Backend URL, e.g. `http://localhost:8000` |
| `NEXT_PUBLIC_APP_NAME` | Display name |
| `NEXT_PUBLIC_MAX_UPLOAD_SIZE_MB` | Client-side upload hint |

---

## Running Locally

**Terminal 1 — API**

```powershell
cd backend
.\.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — UI**

```powershell
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

**Optional smoke test** (backend must be running):

```powershell
cd frontend
npm run smoke-test
```

---

## Testing

### Backend

```powershell
cd backend
.\.venv\Scripts\activate
python -m pytest tests/ -v
```

- Unit tests pass without MongoDB (integration tests skip)
- With MongoDB running: integration tests for DB, upload, auth, etc. also run
- Set `AI_MOCK_MODE=true` in `.env` for CI/local runs without Groq

### Frontend

```powershell
cd frontend
npm test
npm run build
```

---

## Future Enhancements

- Dedicated recommendations page/API
- Email verification + refresh token rotation
- Background workers (Celery/ARQ) for long optimizations at scale
- Additional PDF templates and branding
- Populate and use normalized `skills` taxonomy
- S3-compatible object storage
- OAuth social login
- Recharts lazy-load on job match page (currently in main bundle for that route)

---

## Screenshots

> Insert screenshots in the sections below when preparing your portfolio/demo.

| Section | Suggested capture |
|---------|-----------------|
| **Landing** | Hero + feature highlights (`/`) |
| **Dashboard** | Overall score ring + category chart (`/dashboard`) |
| **Why this score?** | Dialog with dimension explanations |
| **Upload** | Drag-and-drop upload success (`/resumes/upload`) |
| **Job analyzer** | Parsed JD fields (`/jobs/analyze`) |
| **Job match** | Match score + breakdown chart |
| **Skill gap** | Missing skills + roadmap |
| **Bullet improver** | Before/after bullet (`/bullets/improve`) |
| **Optimization review** | Section comparison + accept/reject (`/resumes/optimize/review`) |
| **Versions** | Version list with status badges (`/resumes/versions`) |
| **Mobile** | Dashboard or nav drawer at phone width |

---

## Demo Flow

Use a **fresh test account** and a real PDF/DOCX resume for the best walkthrough.

1. **Register** at `/register` → auto-redirect to dashboard
2. **Upload** at `/resumes/upload` → confirm sections detected
3. **Analyze** on dashboard → wait for scores (button shows spinner; disabled while running)
4. **Why this score?** → open overall or category explanations
5. **Job analyzer** (`/jobs/analyze`) → paste a JD → run analysis
6. **Match** → select your resume → view match score and breakdown
7. **Skill gap** → review missing skills/keywords from match results UI
8. **Bullet improver** → improve one bullet → **Replace** into resume
9. **Optimize** → enter target role → generate → review before/after per section
10. **Accept/reject** changes → **Apply** → note staleness banner if shown
11. **Re-analyze** if prompted → confirm scores refresh
12. **Versions** → see new optimized draft / version history
13. **Download PDF** from dashboard or versions

**Mock mode tip:** With `AI_MOCK_MODE=true`, all AI steps return deterministic sample data instantly — useful for demos without API cost.

---

## License

Private / portfolio project — add your license here if open-sourcing.

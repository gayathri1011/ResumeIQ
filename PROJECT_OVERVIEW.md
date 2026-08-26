# ResumeIQ — Project Overview

**Audience:** mentors, interviewers, recruiters, reviewers, and non-technical stakeholders  
**Project type:** portfolio / demo full-stack AI engineering application — **not** a production-scale recruitment platform  
**Source of truth:** the current repository code (APIs, models, AI tasks, parsers, frontend routes, manifests, and config). Where comments or older docs conflict with code, **code wins**.

---

## 1. Project Summary

ResumeIQ is an AI-assisted resume intelligence web application. A signed-in user uploads a resume, receives an explainable health / ATS-style analysis, pastes a job description to extract requirements and compute a job match (including semantic similarity), reviews skill gaps, improves individual bullets, runs role-targeted optimization with accept/reject review, and can download a generated PDF.

**Primary users (product intent):** students, fresh graduates, job seekers, career switchers, and professionals applying to different roles.

**Also useful for:** portfolio demos, college/project evaluations, technical interviews, mentor reviews, and assessment of full-stack AI engineering skills.

---

## 2. User Workflow (as implemented)

**Authentication is implemented.** Users register and log in with email/password. The API issues JWT access tokens; the frontend stores the token and attaches it to API requests. Resumes, analyses, jobs, matches, and versions are stored in MongoDB and scoped to the authenticated user.

### Actual journey

1. **Landing** (`/`) — product intro; links to Sign up / Log in  
2. **Register or log in** (`/register`, `/login`) — create an account or sign in  
3. **Dashboard** (`/dashboard`) — select a resume; view overall score, category breakdown, “Why this score?” explanations, latest job-match summary when available, PDF download, and quick actions  
4. **Upload master resume** (`/resumes/upload`) — PDF, DOCX, or image (PNG/JPG/JPEG/WEBP/GIF); client and server validation  
5. **Parse & structure** — text extraction (PyMuPDF / python-docx / RapidOCR), then **heuristic section structuring** (not an LLM structuring step at upload). A **Master Resume** version is created (`is_master=True`)  
6. **Analyze** — dashboard Analyze calls the backend; the LLM returns overall score, dimension scores with explanations, and grounded issues  
7. **Optional job flow** (`/jobs/analyze`) — paste JD text → AI extracts title, required/preferred skills, tools, responsibilities, keywords, etc. → match against a selected resume → skill-gap panel (coverage, missing skills, learning roadmap)  
8. **Bullet improver** (`/bullets/improve`) — pick a bullet → AI rewrite (with anti-fabrication checks) → optional **Replace** into the resume version  
9. **Optimize for a target role** (`/resumes/optimize/review`) — target role (stored in browser localStorage per resume; optional JD grounding) → AI proposes section changes with reasons → accept/reject → apply updates live content; a draft optimization version is also created server-side  
10. **Download PDF** — from the dashboard via backend HTML→PDF generation  

### Role-specific versions — accuracy note

| Layer | Behavior |
|-------|----------|
| **Master resume** | Preserved as a master version on upload |
| **Backend** | `POST /api/v1/resumes/{id}/versions/generate` creates a **new role-specific version** from the master (target role, optional company, optional JD text, optional experience level) via AI transformation |
| **Frontend** | `/resumes/versions` and `/resumes/versions/[versionId]` currently **redirect to `/dashboard`**. There is **no dedicated UI** calling the role-version generate endpoint |
| **UI path for role tailoring today** | **Optimize → review → apply**, which creates a draft labeled like `Optimized for {role}` and updates content when applied |

A role version is intended as a **role-tailored transformation** of the master (re-prioritized wording, skills emphasis, summary, bullets) — **not** merely a shortened copy — while preserving the user’s real facts. Fabrication of employers, degrees, or metrics is discouraged by prompts and validators where implemented.

---

## 3. Features List

### A. Resume management

- Authenticated upload and persistence  
- PDF, DOCX, and image support with size/type validation  
- Text extraction and heuristic structured sections (summary, skills, experience, education, projects, certifications, etc., as detected)  
- Master resume version on upload  
- Resume list/detail on dashboard  
- Versions **API**: list, create (duplicate or upload), rename, delete (master protected), analyze/optimize per version, PDF generate, role-version generate  
- Local file storage of originals by default (optional S3 settings exist; not required for the default path)  

### B. AI resume intelligence

- Full-resume AI analysis with overall score (0–100)  
- Dimension scores including: ATS compatibility, skills, experience, projects, education, certifications, achievements, professional summary, keywords, content quality, readability, relevance, quantifiable achievements, action verbs, formatting issues  
- Aggregated category scores on the dashboard: ATS, skills, experience, projects, education, keywords, content quality  
- Per-dimension explanations (“Why this score?”)  
- Issues with severity, category, title, description, suggested fix, grounded-in-resume flag  
- Content-hash caching so unchanged content can reuse prior analysis  

Scores are **application-defined analytical estimates**, not guarantees of any commercial ATS vendor’s result.

### C. Job description intelligence

- Paste raw JD text; optional company  
- AI extraction: job title, required/preferred skills, experience requirements, education requirements, tools, technologies, responsibilities, keywords  
- Persist job descriptions per user  
- Resume ↔ job match with overall score, breakdown (skills, experience, keywords, projects, education), matched/missing skills, missing keywords, explanations  
- Skill-gap view: coverage percent, matched/missing skills (with priority/rationale), learning roadmap; recommendations may be stored internally (no standalone recommendations page)  

### D. Semantic / AI matching

**Implemented (MongoDB float arrays + in-app cosine similarity — not PostgreSQL/pgvector):**

- Embedding generation for resume and job text  
- Vectors stored on MongoDB documents  
- Cosine similarity in application code  
- Semantic score contributes **30%** of the final job match score; structured AI breakdown contributes **70%**  
- Default embedding model: `nomic-embed-text-v1_5` (768 dimensions)  
- If the provider embedding API fails, a **deterministic local hash-based embedding fallback** is used  

**Not implemented:** PostgreSQL, pgvector, Atlas Vector Search, or a dedicated vector database.

Embeddings allow comparison of **meaning** between resume and JD text, not only exact keyword overlap.

### E. Role-specific resume versioning

| Capability | Status |
|------------|--------|
| Master resume preserved | Implemented |
| Separate stored versions | Implemented (API + DB) |
| AI transform for target role (+ optional company / JD / experience level) | Implemented on **backend** |
| Dedicated frontend for generating/browsing role versions | **Not currently implemented** (routes redirect) |
| Role-targeted optimization with accept/reject in UI | Implemented |
| Draft optimization versions labeled by role | Implemented |
| Rename / delete versions (API) | Implemented |
| PDF download for a version | Implemented (dashboard UI + API) |
| Dedicated multi-version comparison product screen | Not present in the live UI |

### F. AI content improvement

- Single-bullet improvement with optional regenerate  
- Replace improved bullet into resume content  
- Full-resume optimization proposals with before/after and “why” notes  
- Accept / reject (and bulk actions) then apply  
- Anti-fabrication checks on bullets/optimization where coded  

### G. Export

- PDF generation from stored structured content (Jinja2 HTML → PyMuPDF `Story`)  
- Download as attachment from the API  

**DOCX export:** not implemented.

### H. Frontend UX

- Responsive App Shell (Dashboard, Upload, Job match, Bullets)  
- Auth pages and JWT-protected API usage  
- Dashboard empty / error / skeleton states  
- Score count-up and circular score motion (Framer Motion)  
- Category breakdown chart (Recharts, lazy-loaded on dashboard)  
- Job match charts (Recharts)  
- Upload step indicator; drag-and-drop style upload UX  
- Job step indicator; inline alerts/errors  
- Optimization section comparison UI  
- Feature skeletons / loading indicators  
- Dialog for “Why this score?”  

**Not found:** a dedicated toast notification library; feedback is largely inline alerts.

### I. Backend / technical

- FastAPI REST API under `/api/v1`  
- Pydantic validation and structured AI output schemas  
- Beanie ODM + Motor (MongoDB)  
- JWT auth: signup, login, logout, `/me`; bcrypt password hashing  
- Ownership checks on resume/job resources  
- Rate limiting on auth and AI-heavy routes  
- CORS configuration  
- AI provider abstraction (Groq default; OpenAI-compatible option; mock mode)  
- File parsing pipeline and PDF service  
- Structured error envelopes  
- pytest suite (behavior and regression helpers — **not** formal ML accuracy benchmarks)  

---

## 4. Tech Stack

### Frontend

| Technology | Why it is used |
|------------|----------------|
| **Next.js 15** (App Router) | Frontend framework and routing |
| **React 19** | UI and client interactivity |
| **TypeScript** | Typed frontend |
| **Tailwind CSS** | Styling |
| **Radix Slot + local UI primitives** | Button/card/dialog-style components (shadcn-like pattern) |
| **Lucide React** | Icons |
| **Framer Motion** | Motion (shell, scores, upload, dialogs) |
| **Recharts** | Dashboard and job-match charts |

### Backend

| Technology | Why it is used |
|------------|----------------|
| **Python 3.11–3.12** (`requires-python >=3.11,<3.13`) | Runtime (OCR deps need &lt;3.13) |
| **FastAPI** | HTTP API |
| **Uvicorn** | ASGI server |
| **Pydantic / pydantic-settings** | Validation and config |
| **Beanie + Motor** | MongoDB ODM / async driver |
| **PyJWT + bcrypt** | Auth |
| **OpenAI SDK / httpx** | Provider-compatible HTTP client |
| **PyYAML** | Prompt loading |
| **Jinja2** | Resume HTML for PDF |

### AI / LLM

| Item | Actual default in code / `.env.example` |
|------|----------------------------------------|
| Provider | **Groq** (`AI_PROVIDER=groq`) |
| Chat model | **`openai/gpt-oss-120b`** |
| Embedding model | **`nomic-embed-text-v1_5`** |
| Optional | `AI_PROVIDER=openai`; `AI_MOCK_MODE=true` for deterministic mocks |

LLM-backed tasks: resume analysis, job description analysis, job matching breakdown, skill-gap enrichment, bullet improvement, resume optimization, role-version transformation (backend).

Chat inference runs on **Groq’s cloud**, not on a local GPU in this repo.

### Resume processing

| Library | Use |
|---------|-----|
| **PyMuPDF (`pymupdf`)** | PDF text extraction; PDF export rendering |
| **python-docx** | DOCX text extraction |
| **Pillow + rapidocr-onnxruntime** | Image resume OCR |

### Database

- **MongoDB 7** (local via `docker-compose.yml`, or hosted Atlas-compatible URL)  
- Embeddings as float arrays; similarity in Python  

**PostgreSQL / pgvector:** not used by the running app. An `alembic/` tree may remain as leftover from an earlier design — it is **not** the active persistence layer.

### Deployment configuration in repo

- `render.yaml` and Python pin (`3.12.8`) for Render-style backend deploy  
- Frontend env `NEXT_PUBLIC_API_BASE_URL` suitable for Vercel or any Next host  
- Known deployed backend example used in project setup: `https://resumeiq-vxu1.onrender.com`

---

## 5. How to Run the Project

Based on the repository README and manifests.

### Prerequisites

- Docker (MongoDB)  
- Python **3.11 or 3.12** (not 3.13+)  
- Node.js 20+  
- Groq API key (or enable mock mode)

### 1. Clone

```powershell
git clone <your-repo-url> resume
cd resume
```

### 2. Database

```powershell
docker compose up -d
```

### 3. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
# Edit .env — set SECRET_KEY, JWT_SECRET_KEY, AI_API_KEY (or AI_MOCK_MODE=true)
uvicorn app.main:app --reload --port 8000
```

Interactive API docs: `http://localhost:8000/api/docs`

### 4. Frontend

```powershell
cd frontend
npm install
copy .env.local.example .env.local
# Set NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev
```

Open `http://localhost:3000`.

### Environment variable names (values not disclosed)

**Backend** (`backend/.env.example` / `Settings`):

| Name | Purpose |
|------|---------|
| `ENVIRONMENT` | Runtime environment label |
| `DEBUG` | Debug logging |
| `SECRET_KEY` | App secret |
| `MONGODB_URL` / `DATABASE_URL` | Mongo connection |
| `MONGODB_DB` | Database name |
| `EMBEDDING_DIMENSIONS` | Embedding vector size (default 768) |
| `CORS_ORIGINS` | Allowed frontend origins |
| `JWT_SECRET_KEY` | JWT signing secret |
| `JWT_ALGORITHM` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime |
| `AUTH_RATE_LIMIT_PER_MINUTE` | Auth throttle |
| `AI_RATE_LIMIT_PER_MINUTE` | AI endpoint throttle |
| `AI_PROVIDER` | `groq` or `openai` |
| `AI_API_KEY` | Provider API key (**server only**) |
| `AI_BASE_URL` | OpenAI-compatible base URL |
| `AI_MODEL` | Chat model id |
| `AI_EMBEDDING_MODEL` | Embedding model id |
| `AI_MAX_RETRIES` | AI retry count |
| `AI_REQUEST_TIMEOUT_SECONDS` | AI timeout |
| `AI_MOCK_MODE` | Mock AI for tests/dev |
| `UPLOAD_MAX_SIZE_MB` | Upload size limit |
| `UPLOAD_ALLOWED_EXTENSIONS` | Allowed file extensions |
| `FILE_STORAGE_BACKEND` | Storage backend (`local` default) |
| `FILE_STORAGE_PATH` | Local upload directory |
| `S3_BUCKET` / `S3_REGION` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` | Optional S3 |

**Frontend** (`frontend/.env.local.example`):

| Name | Purpose |
|------|---------|
| `NEXT_PUBLIC_API_BASE_URL` | Backend origin used by the browser |
| `NEXT_PUBLIC_APP_NAME` | Display name |
| `NEXT_PUBLIC_MAX_UPLOAD_SIZE_MB` | Client upload size hint |

---

## 6. How to Use the App (non-technical)

### Step 1 — Create an account

Sign up with email and password (password must include at least one letter and one number), then log in.

### Step 2 — Upload your master resume

Upload a PDF, Word (DOCX), or image resume. ResumeIQ extracts text and organizes detected sections into a structured master version.

### Step 3 — Review Resume Intelligence

From the dashboard, run analysis. You see an overall score, category scores, charts, explanations of why scores look that way, and prioritized issues.

### Step 4 — Add a target job (optional)

On Job match, paste a job description. ResumeIQ extracts requirements, then compares your resume to the role.

### Step 5 — See job compatibility

You see a match score, breakdown categories, matched and missing skills/keywords, and a skill-gap / learning-roadmap style summary.

### Step 6 — Improve content or optimize for a role

Use Bullet improver for one line at a time, or Optimize to generate role-focused changes, accept or reject each change, and apply.

### Step 7 — Download

Generate and download a PDF of the current version when ready to export.

---

## 7. Current Deployment Status

| Layer | Status |
|-------|--------|
| Frontend | Next.js; env-driven API base URL (suitable for **Vercel**) |
| Backend | FastAPI; **Render**-oriented config (`render.yaml`, Python `3.12.8`) |
| Database | MongoDB (local Docker or hosted Atlas-compatible URL) |
| AI | Groq API for chat (+ embeddings when available; local fallback otherwise) |
| Auth | Implemented; multi-user persistence in MongoDB |
| Local defaults | Local filesystem uploads; mock AI mode for offline/dev |
| Cold starts | Free-tier Render services may cold-start; first API/AI call can be slower |
| Local model loading | RapidOCR ONNX runs in-process for image resumes; chat LLM is remote (Groq) |

Production behavior depends on correct env vars (Mongo, JWT secrets, Groq key, CORS including the Vercel origin).

---

## 8. Data Disclosure

**Collected / processed**

- Account email, password hash, optional full name  
- Uploaded resume files (under configured file storage)  
- Extracted raw text and structured resume JSON  
- Job description text and extracted requirements  
- Analysis, match, optimization, and related AI result payloads  
- Embeddings (float vectors) on resume/job (and version) documents  
- JWT access tokens on the client after login  

**Sent to the AI provider (when mock mode is off)**

- Prompt content derived from resume/JD text and structured JSON needed for the task  

**Persistence**

- User and resume history **are** persisted in MongoDB for authenticated users  
- AI responses may be cached by content/input hash  

**Not claimed**

- Formal privacy certification, DPA packaging, or enterprise data residency controls — not evidenced in code  

---

## 9. Results / Model Performance

**No formal benchmark was found in the current repository.**

What exists instead:

- Application-defined 0–100 scores from LLM structured outputs  
- Weighted job match: **30% semantic similarity + 70% structured breakdown**  
- Automated software tests (pytest / Vitest) for API behavior, validation, and some performance/regression helpers  
- Deterministic mock provider for development without live model calls  

Do not treat resume or match scores as verified real-world hiring outcomes. ATS-style scores are analytical estimates defined by this application.

---

## 10. AI Model / Engineering Disclosure

ResumeIQ combines:

1. **Document parsing** — deterministic extraction + heuristic structuring  
2. **LLM reasoning** — Groq-hosted `openai/gpt-oss-120b` (default) for analysis, JD extraction, match narrative, gaps, bullets, optimization, and backend role-version transform  
3. **Structured outputs** — Pydantic schemas with validation / repair behavior in the AI client  
4. **Embeddings + cosine similarity** — semantic signal for job match  
5. **Rule/weight blending** — fixed 30% / 70% semantic vs structured weights in the matcher  
6. **Safeguards** — prompts and validators discouraging invented employers/dates/metrics  
7. **Caching** — hash-keyed reuse of AI results when inputs are unchanged  
8. **PDF rendering** — template HTML to PDF without another LLM call  

There is **no custom model training** in this repo. The project demonstrates **integration engineering** around a hosted LLM and light embedding logic.

---

## 11. Roadmap — NOT YET IMPLEMENTED

### A. Full role-version product UI

Backend generate exists; dedicated versions browse/create UX is **not** wired (routes redirect to dashboard).

### B. Email verification & refresh tokens

Signup/login use access JWTs only; no email verification or refresh-token rotation as product features.

### C. Background job queue

AI and PDF work run in request handlers (with thread offload for some blocking work) — no Celery/ARQ-style queue as a first-class system.

### D. Multiple PDF templates

Single HTML→PDF path.

### E. Normalized skills taxonomy as runtime matcher

A skills-related model/collection may exist; runtime matching uses AI + embeddings, not a populated skills ontology product.

### F. S3 as default storage

Configured optionally; default is local filesystem.

### G. Standalone recommendations screen

Skill-gap data may be stored; a dedicated Recommendations API/UI is deferred per project docs.

### H. Production-scale ops

Broader observability, queueing, CI/CD polish, and multi-template ATS exports remain roadmap-level.

Some dashboard fix-action labels still say “coming soon” for skill/ATS-specific shortcuts that are not separate screens.

---

## 12. Limitations

- LLM advice can be wrong or incomplete; humans should review before applying.  
- ATS and match scores are heuristic estimates, not vendor ATS scores or interview guarantees.  
- Optimization quality depends on source resume quality and truthful input.  
- Image OCR quality varies with scan quality.  
- Semantic fallback embeddings (when the embed API fails) are weaker than true model embeddings.  
- Free-tier API and host cold starts can add latency or rate-limit failures.  
- Role-version **API** capability is ahead of the **versions UI**.  
- Not positioned as an enterprise ATS or applicant-tracking system of record.

---

## 13. Project Positioning

ResumeIQ is a **working portfolio demonstration** of a practical career-product workflow built with:

- modern frontend engineering  
- FastAPI backend design  
- document parsing (PDF/DOCX/OCR)  
- hosted LLM integration with structured outputs  
- embeddings and similarity scoring  
- MongoDB persistence and authentication  
- explainable scoring and optimization review  
- PDF export  

> **A working demonstration of how AI can be integrated into a practical career-product workflow.**

Evaluate it as a full-stack AI engineering sample — **not** as a production recruitment platform.

---

## 14. Accuracy note

This overview was produced by inspecting frontend routes/features, backend routers/services/AI tasks/parsers/models/config, dependency manifests, Docker Compose, Render Python pin, and tests. Features described only in older comments/READMEs but not wired (for example, a dedicated versions UI, PostgreSQL/pgvector, or DOCX export) are marked **not implemented** or deferred above.

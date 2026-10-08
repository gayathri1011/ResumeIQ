# ResumeIQ — Current Project Overview

**Audience:** project reviewers, developers, and product stakeholders
**Source of truth:** current frontend routes/components, backend routers/services/models, AI tasks/prompts, manifests, and deployment configuration. The implementation—not older documentation—is authoritative.

## 1. Product Summary

ResumeIQ is a full-stack resume analysis and job-fit application. An authenticated user uploads a resume, reviews an AI-generated assessment, analyzes a pasted job description, compares job requirements with the resume, and can request career-trajectory and recruiter-first-impression reports.

The codebase also contains backend APIs for resume optimization, versions, role transformations, and PDF generation. Several of those capabilities do not currently have a reachable frontend screen; their implementation status is called out below rather than presented as available UI.

### Problem and objective

Applicants often lack specific feedback about resume content and how it relates to a target job. ResumeIQ aims to turn resume text and a job description into structured, explainable feedback. Its scores are application-generated assessments, not results from a commercial applicant-tracking system or predictions of hiring outcomes.

## 2. Current User Experience

### Active frontend routes

| Route | Current experience |
|---|---|
| `/` | Public product introduction with links to registration and login. |
| `/register` | Email/password account creation; full name is optional. Successful signup stores the access token and navigates to the dashboard. |
| `/login` | Email/password login; successful login stores the access token and navigates to the safe requested destination or dashboard. |
| `/dashboard` | Loads the user's resumes, selects a recent resume, shows analysis state and scores, category breakdowns, explanations, and navigation actions. Empty, loading, and error states are present. |
| `/resumes/upload` | Select or drop a PDF, DOCX, or supported image; upload progress and parsing result/error are shown. |
| `/jobs/analyze` | Paste a job description, extract structured requirements, choose a resume, run a match, then request a skill-gap report. |
| `/career-trajectory` | Request and review adjacent role paths, readiness factors, skills/proof gaps, and next steps for a selected resume. |
| `/recruiter-lens` | Request and review a resume-first-impression report, visibility estimates, attention map, strengths, risks, and suggestions. |

The shared authenticated navigation links to Dashboard, Upload, Job match, Career trajectory, and Recruiter Lens. It collapses to a mobile menu on small screens.

### Routes and components not currently exposed as working pages

- `/resumes/versions` and `/resumes/versions/[versionId]` redirect to `/dashboard`. Version APIs and data models exist, but there is no active version-management screen.
- `/resumes/optimize/review` redirects to `/dashboard`. An optimization-review component and client service exist in source, but no current route mounts that component.
- The `frontend/app/bullets` route tree and `frontend/features/bullet` directory are empty. There is no current bullet-rewriting API or user-facing bullet feature.
- A PDF download button component and PDF API endpoint exist, but the button is not referenced by an active page. PDF export is therefore an API capability, not a currently reachable user workflow.

## 3. Architecture

```text
Browser (Next.js / React)
  ├─ App Router pages and feature components
  ├─ sessionStorage JWT bearer token
  └─ typed service modules and shared API client
          │ HTTPS, JSON or multipart/form-data
          ▼
FastAPI (/api/v1)
  ├─ authentication, validation, CORS, rate limits, error envelopes
  ├─ routers → orchestration services → repositories
  ├─ parsers, AI task modules, prompt templates, PDF renderer
  ├─ MongoDB through Beanie and Motor
  └─ local filesystem for uploaded originals by default
          │
          ├─ Groq OpenAI-compatible API by default; OpenAI-compatible provider optional
          └─ MongoDB configured by environment
```

The frontend uses the shared `API_BASE_URL` and modules under `frontend/services/`. Those modules provide `/api/v1/...` paths; `frontend/lib/api-client.ts` joins them to the configured backend origin. JSON requests use `fetch`; multipart resume uploads use `XMLHttpRequest` to report progress.

The backend mounts `api_v1_router` at `/api/v1`. Routers delegate to services, which coordinate parsers, AI tasks, repositories, and response schemas. Beanie document models persist to MongoDB. There is no PostgreSQL runtime or separate vector database.

## 4. Authentication, Requests, and Errors

- Signup and login accept email/password; signup also accepts optional full name. Passwords are bcrypt-hashed and the API returns a signed JWT access token.
- Tokens are stored in browser `sessionStorage` and attached as `Authorization: Bearer ...` on API requests, including upload XHRs. Logout discards the client token; the backend access token is stateless.
- The auth provider allows the landing, login, and register routes without a token and redirects protected routes to login when unauthenticated. There is no refresh-token rotation, email verification, or OAuth flow in the current implementation.
- Resume and job services enforce authenticated ownership for their records. Logout and `/auth/me` require authentication; signup, login, and health are public.
- Auth and AI-heavy routes use an in-process, per-client-IP rate limiter. It is not a distributed rate limiter.
- Application and validation errors use a JSON envelope with `error.code`, `error.message`, and optional `error.details`. Database errors are mapped to structured responses. Browser-level request failures are converted by the frontend into generic network errors, which can obscure whether the underlying browser error was a CORS, connection, or other fetch/XHR failure.

## 5. Resume Upload and Document Processing

1. The upload UI validates extension, MIME type, non-empty content, and the configured client size limit, then posts multipart form data to `POST /api/v1/resumes/upload`.
2. The FastAPI route requires a bearer-authenticated user. `ResumeService` applies server-side extension, MIME, empty-file, and size checks (10 MB by default).
3. The service temporarily writes the content, dispatches to a format-specific parser, removes the temporary file, then saves the original under the configured local storage directory and persists extracted content.
4. Upload creates the resume record and its initial master `ResumeVersion`. Resume embedding generation is attempted after parsing; an embedding error is logged and does not fail the upload.

### Supported parsing

| Format | Current implementation |
|---|---|
| PDF | PyMuPDF text extraction; text size is one heading signal. Scanned PDFs are not automatically OCRed by the PDF parser. |
| DOCX | `python-docx` paragraph extraction; heading styles and short bold paragraphs provide heading signals. |
| PNG/JPG/JPEG/WEBP/GIF | RapidOCR/ONNX Runtime extracts image text; short all-caps lines help identify headings. |

Shared Python parsing code normalizes lines, matches known section-heading aliases, and uses regular expressions and simple rules to structure personal information, summary, skills, experience, education, projects, certifications, achievements, and links. Upload structuring is heuristic, not an LLM extraction step. Results include detected/missing section metadata. OCR quality depends on the image.

Original files use the local filesystem implementation under `FILE_STORAGE_PATH` (default `./uploads`). S3 settings are present, but `get_file_storage()` currently implements only local storage; selecting another backend raises `NotImplementedError`. `render.yaml` does not configure a persistent disk, so durable uploaded-file storage on Render must be configured separately if required.

## 6. Resume Analysis and Dashboard

Analysis is initiated from the dashboard after upload; upload itself does not run resume scoring. The authenticated `POST /api/v1/resumes/{resume_id}/analyze` route calls `ResumeAnalyzer` with the parsed structure and raw text. The AI response is validated against a Pydantic schema and contains an overall 0–100 score, category scores, dimension explanations, summary, and evidence-linked issues/suggested fixes.

The dashboard displays the latest analysis, category breakdowns, “Why this score?” explanations, and stale/re-analysis indicators. Resume analysis and related AI payloads are persisted; content hashes allow reuse when the parsed input has not changed. Scores are model-generated assessments, not verified ATS scores.

## 7. Job Description, Matching, and Skill Gaps

1. The user pastes a job posting in `/jobs/analyze`; the UI checks for a minimum-length description and can associate a resume.
2. `POST /api/v1/jobs/analyze` validates and normalizes the text. `JobDescriptionAnalyzer` uses a YAML prompt and structured AI output to extract role title, required/preferred skills, experience/education requirements, tools, technologies, responsibilities, and keywords. It stores the raw text, parsed requirements, and an embedding.
3. `POST /api/v1/jobs/{job_id}/match` checks ownership and calls `JobMatcher`. The matcher compares the parsed resume structure with parsed job requirements using a structured AI rubric. Its saved score is the weighted average of structured subscores: skills 35%, experience 25%, keywords 15%, project relevance 15%, and education 10%.
4. The current matcher sets `semantic_score` to `null`; it does **not** combine cosine similarity with the structured score. Embeddings are generated/stored, but are not currently consumed by match scoring. A cosine-similarity helper and local embedding fallback exist in code, but are not part of current match ranking.
5. Skill-gap retrieval uses existing match/JD data. Skill-name normalization and containment rules derive coverage and prioritize missing skills; required skills have weight 1.0, while preferred skills, tools, and technologies have weight 0.5. An AI task supplies explanations and a learning roadmap. Recommendations are persisted internally, but there is no standalone recommendations route or screen.

The match report includes the structured breakdown, matched/missing skills and keywords, explanatory text, cache status, and timestamps. It is not a measurement of a third-party ATS.

## 8. Other AI Capabilities

| Capability | What current code does | User access/status |
|---|---|---|
| Career Trajectory | AI proposes possible roles from resume evidence; backend calculates deterministic readiness factors and returns skill gaps, proof gaps, and next steps. Results are cached by resume content/prompt version. | Active `/career-trajectory` page; requires a parsed resume and asks the user to run the report. |
| Recruiter 10-Second Lens | AI returns a recruiter snapshot, first impression, strengths, risks, and suggestions. Backend derives visibility scores and an attention map from resume structure; these are estimates, not real eye-tracking. | Active `/recruiter-lens` page. |
| Resume optimization | Backend can request a role- or job-grounded proposal, validates output against structural facts and fabrication checks, stores changes, and accepts/rejects them through an apply endpoint. | API/service code exists; the current review route redirects to the dashboard, so this workflow is not reachable from the current UI. |
| Resume versions and role transformation | Backend supports listing, creating, renaming, deleting, analyzing, optimizing, transforming for a role, and exporting versions. Upload creates the master version. | APIs exist; version pages redirect to the dashboard. No active version-management or role-transformation UI is wired. |
| Bullet improvement | No current backend endpoint, feature implementation, or active route was found. | Not implemented. |
| PDF export | Backend renders stored version content through a Jinja2 HTML template and PyMuPDF `Story` to a PDF stream. | API exists at the version `generate` endpoint; a frontend button component exists but is not imported by an active route. |

## 9. AI, Prompts, Embeddings, and Retrieval

- `AIService` is the shared structured-completion facade. It selects the mock provider when `AI_MOCK_MODE=true`, otherwise Groq by default or the OpenAI-compatible provider when configured. The Groq provider uses the OpenAI SDK against Groq's compatible endpoint.
- Defaults are `AI_PROVIDER=groq`, chat model `openai/gpt-oss-120b`, embedding model `nomic-embed-text-v1_5`, and 768 embedding dimensions. Provider credentials remain server-side.
- Task-specific YAML prompts cover resume analysis, job analysis, matching, skill gaps, optimization, role transformation, recruiter lens, and career trajectory. The loader reads YAML with PyYAML; task code formats the user prompt and validates returned JSON with Pydantic. Malformed structured output can be retried with a repair instruction. Model/prompt metadata and token usage are stored when returned by the provider.
- The OpenAI-compatible provider requests embeddings. If the embedding model returns a not-found response, code falls back to a deterministic local hash-based text vector. This is not a trained embedding model.
- Resume, version, and job documents have float-array embedding fields. There is no MongoDB vector index, Atlas Vector Search, pgvector, or dedicated vector database in the current matching path. The normalized skill collections are registered as models but the current matcher does not use them.
- No custom model training, labeled dataset, formal accuracy/precision/recall/F1 benchmark, or hiring-outcome evaluation is included in the repository.

## 10. Data Layer

The application uses MongoDB through Motor and Beanie. `MongoDocument` supplies UUID identifiers and timestamps; repositories wrap document operations. Main collections registered at startup include:

| Collection | Purpose |
|---|---|
| `users` | Email, password hash, optional full name. |
| `resumes` | Owner, original file metadata/path, raw text, parsed structure, optional embedding. |
| `resume_versions` | Numbered resume snapshots, source/status, target-role metadata, optional embedding. |
| `resume_analyses` | Overall/category scores, issues, status, timestamps. |
| `job_descriptions` | Owner, raw JD, parsed requirements, optional embedding. |
| `job_matches` | Resume/JD references, score, breakdown, matched/missing terms. |
| `ai_analysis_results` | Structured AI payloads, input hashes, model/prompt metadata, token usage, linked records. |
| `recommendations` | Skill-gap-derived recommendation records. |
| `skills`, `resume_skills`, `job_required_skills` | Normalized skill models/repositories exist, but are not used by the current match flow. |

Repositories and ownership helpers scope user-facing resume/job operations. Startup attempts Mongo initialization; the app logs initialization failure so health can still answer, while data-dependent routes cannot operate without the database. Local development can use the MongoDB 7 service in `docker-compose.yml`; hosted environments supply their Mongo connection through environment variables.

## 11. API Surface

Base prefix: `/api/v1`. Local interactive documentation is served at `/api/docs`.

| Area | Implemented paths (relative to `/api/v1`) |
|---|---|
| Health | `GET /health` |
| Authentication | `POST /auth/signup`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` |
| Resume core | `GET /resumes`, `POST /resumes/upload`, `GET /resumes/{resume_id}`, `POST /resumes/{resume_id}/analyze` |
| Resume insights | `POST /resumes/{resume_id}/trajectory`, `POST /resumes/{resume_id}/recruiter-lens`, `GET /resumes/{resume_id}/matches`, `GET /resumes/{resume_id}/skill-gap` |
| Jobs | `GET /jobs`, `POST /jobs/analyze`, `GET /jobs/{job_id}`, `POST /jobs/{job_id}/match`, `GET /jobs/{job_id}/skill-gap` |
| Optimization API | `POST /resumes/{resume_id}/optimize`, `GET /resumes/{resume_id}/optimization/latest`, `POST /resumes/{resume_id}/optimization/apply` |
| Version API | `GET/POST /resumes/{resume_id}/versions`, `GET/PATCH/DELETE /resumes/{resume_id}/versions/{version_id}`, `POST /resumes/{resume_id}/versions/generate`, `GET /resumes/{resume_id}/versions/{version_id}/transformation`, and version-scoped analyze/optimize/PDF-generate endpoints |

Protected endpoints use `Authorization: Bearer <access_token>`. Resume upload uses multipart field `file`; version creation also accepts multipart fields. All paths above are implemented in routers, but only the active frontend routes described above are currently exposed to users.

## 12. Technology and Configuration

### Frontend

Next.js 15 App Router, React 19, TypeScript, Tailwind CSS, local/Radix-based UI primitives, Lucide React, Framer Motion, and Recharts. Vitest is configured for frontend tests. `@/*` resolves to the frontend root.

`NEXT_PUBLIC_API_BASE_URL` is the backend **origin**; service paths already include `/api/v1`. The local `.env.local.example` uses `http://localhost:8000`. `frontend/lib/constants.ts` falls back to that local origin outside production and to `https://resumeiq-vxu1.onrender.com` in production if the variable is unset. Vercel public environment values are embedded at build time; do not append a second `/api/v1` to the base URL.

### Backend

Python `>=3.11,<3.13`; Render pins Python `3.12.8`. FastAPI/Uvicorn, Pydantic v2 and pydantic-settings, Beanie/Motor/PyMongo, PyJWT/bcrypt, the OpenAI SDK, PyYAML, PyMuPDF, python-docx, Pillow/RapidOCR ONNX Runtime, aiofiles, and Jinja2 are declared in `backend/pyproject.toml` / `requirements.txt`.

### Key environment groups

- Backend: Mongo URL/database; JWT secret/algorithm/expiry; CORS origins/regex; auth/AI rate limits; AI provider, key, model, timeouts/retries/mock mode; upload size/extensions; file storage backend/path.
- Frontend: `NEXT_PUBLIC_API_BASE_URL`, display name, and client upload-size hint. No AI secret belongs in frontend variables.
- The backend `.env.example` is a template, not a live deployment configuration. Never copy secrets into this document.

## 13. Deployment and Local Operation

### Deployment configuration in this repository

- `render.yaml` defines the FastAPI web service, runs Uvicorn on Render's `$PORT`, pins Python `3.12.8`, and configures a regex for `https://*.vercel.app` origins. Custom frontend domains must be included in the Render `CORS_ORIGINS` environment value.
- The Next.js frontend is deployed separately to Vercel; no Vercel deployment manifest is present in the repository. Production requires `NEXT_PUBLIC_API_BASE_URL` to name the Render origin, without `/api/v1`.
- `docker-compose.yml` defines only MongoDB 7 for local development; it does not start the frontend or backend.
- At review time, the observed production frontend was `https://frontend-liard-phi-22.vercel.app` and its loaded bundle used `https://resumeiq-vxu1.onrender.com`.

### Local startup

1. Start MongoDB with `docker compose up -d` from the repository root.
2. In `backend/`, create and activate a virtual environment, install `pip install -e ".[dev]"`, copy `.env.example` to `.env`, and configure database/JWT/AI settings. Run `uvicorn app.main:app --reload --port 8000`.
3. In `frontend/`, install with `npm ci`, copy `.env.local.example` to `.env.local`, keep `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`, and run `npm run dev`.
4. Open `http://localhost:3000`; health is at `http://localhost:8000/api/v1/health`.

## 14. Current vs. Not Implemented

### Currently implemented

Authentication, protected resume upload and parsing, dashboard analysis and explanations, job-description extraction/matching, skill-gap reports, Career Trajectory, Recruiter 10-Second Lens, Mongo persistence, AI result caching, local original-file storage, and backend APIs for optimization/version/PDF workflows.

### Not implemented or not exposed as user workflows

- No active bullet-improvement feature or bullet API.
- No active version browsing/management or optimization-review route; current route files redirect to the dashboard even though related backend APIs and some frontend components exist.
- No active PDF download entry point in the current pages; the API and an unreferenced button component exist.
- No standalone recommendations API/screen, email verification, refresh tokens, OAuth, background job queue, S3 storage implementation, vector database, custom model training, or formal ML benchmark.
- The repository does not define a committed product roadmap. The items above describe omissions, not promised delivery dates.

## 15. Tests, Limitations, and Data Handling

Backend tests live under `backend/tests` and use pytest; database-backed fixtures skip when MongoDB is unavailable. The suite covers API/auth, upload/parsing, analysis, matching, optimization, recruiter lens, trajectory, rate limits, and other feature behavior. Frontend tests use Vitest. These are software behavior checks, not model-quality benchmarks.

The application processes account email, password hashes, uploaded files, extracted resume text/structure, job descriptions, AI outputs, and related records. When mock mode is off, task-specific resume/JD-derived prompts are sent to the configured AI provider. MongoDB is the application data store; original files default to local disk. Review deployment storage and provider/data policies before using sensitive production resumes.

Known implementation constraints include heuristic document structuring, variable OCR quality, model-dependent advice, synchronous request-time AI work, in-memory rate limits, local-only file storage, and a mismatch between some backend APIs and currently reachable frontend screens. Scores and recruiter/trajectory estimates must not be represented as verified hiring outcomes.
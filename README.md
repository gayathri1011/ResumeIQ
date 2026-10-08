# ResumeIQ

ResumeIQ is a full-stack resume analysis and job-fit application. The detailed, code-verified architecture, feature status, API surface, and deployment notes are in [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md).

## Local development

Prerequisites: Node.js, Python 3.11 or 3.12, and Docker for the local MongoDB service.

1. Start MongoDB from the repository root:

   ```sh
   docker compose up -d
   ```

2. Configure and start the backend:

   ```sh
   cd backend
   python -m venv .venv
   # Activate .venv for your shell, then:
   pip install -e ".[dev]"
   # Copy .env.example to .env and set MongoDB/JWT/AI values.
   uvicorn app.main:app --reload --port 8000
   ```

   Health check: `http://localhost:8000/api/v1/health`
   API docs: `http://localhost:8000/api/docs`

3. Configure and start the frontend in a separate terminal:

   ```sh
   cd frontend
   npm ci
   # Copy .env.local.example to .env.local.
   npm run dev
   ```

   Open `http://localhost:3000`. The local frontend API origin is `http://localhost:8000`.

## Tests

```sh
cd backend && python -m pytest
cd frontend && npm test
```

See [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) for current feature exposure, API paths, architecture, AI behavior, persistence, deployment, and known limitations. Secrets belong only in local/server environment files; do not commit them or expose backend AI credentials through `NEXT_PUBLIC_*` variables.
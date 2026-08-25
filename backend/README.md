# ResumeIQ Backend

FastAPI backend for ResumeIQ. See the root `README.md` for full project documentation.

## Quick start

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env

# Start MongoDB (from repo root)
docker compose up -d

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: `GET http://localhost:8000/api/v1/health`

## Database

- **ODM:** Beanie 1.26.0 on Motor (async MongoDB)
- **Server:** MongoDB 7 via `docker compose` (`mongodb://localhost:27017`, database `resumeiq`)
- **Indexes:** declared on Beanie document `Settings`; created at `init_beanie` on startup
- **Embeddings:** stored as float arrays; cosine similarity runs in Python (not Atlas Vector Search)

Do not run Alembic. The `alembic/` folder is leftover from the previous PostgreSQL stack and is unused.

Pin **Beanie 1.26.0**. Newer Beanie releases can break Motor (`MotorDatabase object is not callable`).

## Tests

```bash
pytest                          # unit tests (Mongo optional; integration fixtures skip if it is down)
pytest tests/integration -v     # integration tests (requires MongoDB on localhost:27017)
```

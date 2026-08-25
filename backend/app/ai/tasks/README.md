# AI Task Services

Per-task AI services that consume the shared AIService:

- `resume_analyzer.py` — health score and explainability
- `job_matcher.py` — JD parsing and match narrative
- `resume_optimizer.py` — role-targeted rewrites
- `bullet_improver.py` — before/after bullet improvements

Each task loads prompts from `app/ai/prompts/` and validates output via `app/ai/schemas/`.

# Alembic (unused)

This folder is leftover from when ResumeIQ used PostgreSQL + SQLAlchemy.

The app now uses **MongoDB** with Beanie. Schema is applied via document models at startup (`init_beanie`). Do not run `alembic upgrade`.

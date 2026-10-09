# AI prompts

Versioned prompt data is stored in YAML files and loaded with PyYAML by `loader.py`. Task modules format each `user_template` with Python string formatting, then validate model responses against Pydantic schemas.

Current prompt files cover resume analysis, job analysis/matching, skill gaps, optimization, role transformation, career trajectory, and recruiter lens. Prompt presence does not by itself imply that a corresponding frontend workflow is currently exposed; see the root `PROJECT_OVERVIEW.md`.

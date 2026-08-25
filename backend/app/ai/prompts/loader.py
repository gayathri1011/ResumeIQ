"""Load versioned prompt templates from app/ai/prompts/."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

PROMPTS_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=16)
def load_prompt(name: str) -> dict[str, str]:
    path = PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "system" not in data:
        raise ValueError(f"Invalid prompt file: {path}")
    return {"system": str(data["system"]), "user_template": str(data.get("user_template", ""))}

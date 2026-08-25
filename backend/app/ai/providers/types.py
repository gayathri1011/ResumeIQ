"""Provider completion result."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CompletionResult:
    content: str
    model_used: str
    token_usage: dict[str, Any] | None = None

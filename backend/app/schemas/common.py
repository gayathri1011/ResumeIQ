import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampSchema(BaseSchema):
    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseModel):
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=100)


class HealthResponse(BaseModel):
    status: str
    environment: str
    version: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


def sanitize_target_role(value: str) -> str:
    """Validate and sanitize a target role string against prompt injection and malformed input."""
    if not isinstance(value, str):
        raise ValueError("Target role must be a string.")

    # Strip control characters (ASCII 0-31 and 127)
    cleaned = "".join(ch for ch in value if ord(ch) >= 32 and ord(ch) != 127)

    # Defang common prompt injection patterns
    injection_patterns = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"disregard\s+(all\s+)?instructions",
        r"system\s*prompt",
        r"<\/?system>",
        r"<\|im_start\|>",
        r"<\|im_end\|>",
        r"you\s+are\s+now\s+a",
        r"(^|\n)\s*(system|assistant|user)\s*:",
    ]
    for pattern in injection_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    # Collapse whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Enforce minimum and maximum bounds
    if len(cleaned) < 2:
        raise ValueError("Target role must be at least 2 characters.")
    if len(cleaned) > 100:
        cleaned = cleaned[:100].strip()

    # Must contain letters or numbers
    if not re.search(r"[a-zA-Z0-9]", cleaned):
        raise ValueError("Target role must contain letters or numbers.")

    return cleaned

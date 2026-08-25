"""Groq provider — OpenAI-compatible API at api.groq.com."""

from __future__ import annotations

from app.ai.providers.openai_provider import OpenAIProvider
from app.core.config import settings

GROQ_DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"


class GroqProvider(OpenAIProvider):
    def __init__(self) -> None:
        super().__init__(base_url=settings.ai_base_url or GROQ_DEFAULT_BASE_URL)

"""AIService facade — single entry point for all AI provider calls."""

from __future__ import annotations

import json
import logging
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.ai.errors import AIConfigError, AIOutputValidationError, AIProviderError
from app.ai.providers.groq_provider import GroqProvider
from app.ai.providers.mock_provider import MockAIProvider
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.providers.types import CompletionResult
from app.core.config import settings

AIProvider = GroqProvider | OpenAIProvider | MockAIProvider

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

REPAIR_INSTRUCTION = (
    "Your previous response was invalid. Fix it to match the required JSON schema exactly. "
    "Validation errors:\n{errors}\n\n"
    "Return ONLY corrected JSON with no markdown."
)


def get_ai_provider() -> AIProvider:
    if settings.ai_mock_mode:
        return MockAIProvider()
    provider = settings.ai_provider.lower()
    if provider == "groq":
        return GroqProvider()
    if provider == "openai":
        return OpenAIProvider()
    raise AIConfigError(f"Unsupported AI provider: {settings.ai_provider}")


class AIService:
    """Structured completions with retry/repair for malformed JSON."""

    def __init__(self, provider: AIProvider | None = None) -> None:
        self._provider = provider or get_ai_provider()

    async def complete_structured(
        self,
        *,
        prompt: str,
        system_prompt: str,
        output_schema: type[T],
        prompt_version: str,
        **kwargs: Any,
    ) -> tuple[T, CompletionResult]:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        last_errors: str | None = None
        last_content: str | None = None
        max_attempts = settings.ai_max_retries + 1

        for attempt in range(max_attempts):
            try:
                result = await self._provider.complete(messages, **kwargs)
                last_content = result.content
                parsed = self._parse_and_validate(result.content, output_schema)
                return parsed, result
            except (json.JSONDecodeError, ValidationError) as exc:
                last_errors = str(exc)
                logger.warning(
                    "AI output validation failed (attempt %s/%s): %s",
                    attempt + 1,
                    max_attempts,
                    last_errors,
                )
                if attempt < max_attempts - 1 and last_content is not None:
                    messages.append({"role": "assistant", "content": last_content})
                    messages.append(
                        {
                            "role": "user",
                            "content": REPAIR_INSTRUCTION.format(errors=last_errors),
                        }
                    )
            except AIProviderError:
                raise

        raise AIOutputValidationError(
            f"AI output failed validation after {max_attempts} attempts."
        )

    def _parse_and_validate(self, content: str, output_schema: type[T]) -> T:
        data = json.loads(content)
        return output_schema.model_validate(data)

    async def embed(self, text: str) -> list[float]:
        return await self._provider.embed(text)


def get_ai_service() -> AIService:
    return AIService()

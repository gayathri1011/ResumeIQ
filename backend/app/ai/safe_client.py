"""Robust AIService extension with timeout handling, empty response guards,
single bounded repair retry, server-side sanitized logging, and deterministic fallbacks.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.ai.client import REPAIR_INSTRUCTION, AIService, get_ai_service
from app.ai.errors import AIOutputValidationError, AITimeoutError
from app.ai.prompts.loader import load_prompt
from app.ai.providers.types import CompletionResult
from app.core.config import settings
from app.core.exceptions import AppError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class RobustAIService:
    """Hardened AI client wrapper ensuring graceful degradation and zero raw leakages."""

    def __init__(self, ai_service: AIService | None = None) -> None:
        self.ai_service = ai_service or get_ai_service()

    async def run_task(
        self,
        prompt_name: str,
        template_vars: dict[str, Any],
        output_schema: type[T],
        fallback_factory: Callable[[], T] | None = None,
        timeout_seconds: float | None = None,
        **kwargs: Any,
    ) -> T:
        prompt_file = f"{prompt_name}.yaml" if not prompt_name.endswith(".yaml") else prompt_name
        prompt_data = load_prompt(prompt_file)
        user_prompt = prompt_data["user_template"].format(**template_vars)
        system_prompt = prompt_data["system"]
        parsed, _ = await self.complete_safe(
            prompt=user_prompt,
            system_prompt=system_prompt,
            output_schema=output_schema,
            prompt_version=prompt_name,
            fallback_factory=fallback_factory,
            timeout_seconds=timeout_seconds,
            **kwargs,
        )
        return parsed

    async def complete_safe(
        self,
        *,
        prompt: str,
        system_prompt: str,
        output_schema: type[T],
        prompt_version: str,
        fallback_factory: Callable[[], T] | None = None,
        timeout_seconds: float | None = None,
        **kwargs: Any,
    ) -> tuple[T, CompletionResult]:
        """Execute structured completion with timeout, empty check, 1 repair retry, and fallback."""
        timeout = timeout_seconds or getattr(settings, "ai_request_timeout", 45.0)

        try:
            return await asyncio.wait_for(
                self._execute_with_repair(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    output_schema=output_schema,
                    prompt_version=prompt_version,
                    **kwargs,
                ),
                timeout=timeout,
            )
        except TimeoutError as exc:
            logger.error(
                "AI request timed out after %s seconds for prompt %s: %s",
                timeout,
                prompt_version,
                exc,
                exc_info=True,
            )
            if fallback_factory is not None:
                logger.warning("Invoking deterministic fallback due to timeout on %s", prompt_version)
                return fallback_factory(), CompletionResult(
                    content="",
                    model_used="deterministic-fallback-timeout",
                    token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                )
            raise AITimeoutError("AI analysis timed out. Please try again.") from exc

        except Exception as exc:
            logger.error(
                "AI execution error on %s: %s",
                prompt_version,
                exc,
                exc_info=True,
            )
            if fallback_factory is not None:
                logger.warning("Invoking deterministic fallback due to error on %s", prompt_version)
                return fallback_factory(), CompletionResult(
                    content="",
                    model_used="deterministic-fallback-error",
                    token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                )
            if isinstance(exc, AppError):
                raise
            raise AppError(
                "The AI service is temporarily unavailable. Please try again.",
                code="ai_service_error",
                status_code=502,
            ) from exc

    async def _execute_with_repair(
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

        provider = self.ai_service._provider  # type: ignore[attr-defined]

        # Attempt 1
        result = await provider.complete(messages, **kwargs)
        content = (result.content or "").strip()

        if not content:
            logger.warning("AI provider returned empty response on attempt 1 for %s", prompt_version)
            validation_error = "Response was empty."
        else:
            try:
                parsed = self._parse_and_validate(content, output_schema)
                return parsed, result
            except (json.JSONDecodeError, ValidationError) as exc:
                validation_error = str(exc)
                logger.warning(
                    "AI output validation failed on attempt 1 for %s: %s",
                    prompt_version,
                    validation_error,
                )

        # Exactly ONE bounded repair/retry
        messages.append({"role": "assistant", "content": content or "{}"})
        messages.append({"role": "user", "content": REPAIR_INSTRUCTION.format(errors=validation_error)})

        repair_result = await provider.complete(messages, **kwargs)
        repair_content = (repair_result.content or "").strip()

        if not repair_content:
            raise AIOutputValidationError("AI returned empty output after repair attempt.")

        try:
            parsed = self._parse_and_validate(repair_content, output_schema)
            return parsed, repair_result
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.error("AI output failed validation after repair attempt for %s: %s", prompt_version, exc)
            raise AIOutputValidationError(f"AI output failed validation after repair: {exc}") from exc

    def _parse_and_validate(self, content: str, output_schema: type[T]) -> T:
        # Strip potential markdown fences if present
        clean = content.strip()
        if clean.startswith("```"):
            lines = clean.splitlines()
            if len(lines) >= 3 and lines[-1].strip() == "```":
                clean = "\n".join(lines[1:-1]).strip()
        data = json.loads(clean)
        return output_schema.model_validate(data)


def get_robust_ai_service(ai_service: AIService | None = None) -> RobustAIService:
    return RobustAIService(ai_service)

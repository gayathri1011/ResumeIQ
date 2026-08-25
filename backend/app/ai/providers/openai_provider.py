"""OpenAI-compatible chat/embeddings client (OpenAI or Groq)."""

from __future__ import annotations

import logging
from typing import Any

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, NotFoundError, RateLimitError

from app.ai.errors import AIConfigError, AIProviderError, AIRateLimitError, AITimeoutError
from app.ai.local_embeddings import local_text_embedding
from app.ai.providers.types import CompletionResult
from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """Calls an OpenAI-compatible Chat Completions + Embeddings API."""

    def __init__(self, *, base_url: str | None = None) -> None:
        if not settings.ai_api_key:
            raise AIConfigError("AI_API_KEY is not configured.")
        client_kwargs: dict[str, Any] = {
            "api_key": settings.ai_api_key,
            "timeout": settings.ai_request_timeout_seconds,
        }
        resolved_base = base_url or settings.ai_base_url
        if resolved_base:
            client_kwargs["base_url"] = resolved_base
        self._client = AsyncOpenAI(**client_kwargs)
        self.model = settings.ai_model
        self.embedding_model = settings.ai_embedding_model

    async def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> CompletionResult:
        model = str(kwargs.get("model", self.model))
        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                response_format={"type": "json_object"},
                temperature=kwargs.get("temperature", 0.2),
            )
        except RateLimitError as exc:
            raise AIRateLimitError() from exc
        except APITimeoutError as exc:
            raise AITimeoutError() from exc
        except APIConnectionError as exc:
            raise AIProviderError("Could not connect to the AI service.") from exc
        except NotFoundError as exc:
            raise AIProviderError(
                f"AI model '{model}' is not available. Update AI_MODEL in backend/.env.",
            ) from exc
        except Exception as exc:
            logger.exception("AI API error")
            raise AIProviderError() from exc

        content = response.choices[0].message.content
        if not content:
            raise AIProviderError("AI returned an empty response.")

        token_usage = None
        if response.usage:
            token_usage = {
                "input": response.usage.prompt_tokens,
                "output": response.usage.completion_tokens,
                "total": response.usage.total_tokens,
            }

        return CompletionResult(content=content, model_used=model, token_usage=token_usage)

    async def embed(self, text: str) -> list[float]:
        try:
            response = await self._client.embeddings.create(
                model=self.embedding_model,
                input=text,
            )
            return list(response.data[0].embedding)
        except NotFoundError:
            logger.warning(
                "Embedding model %s unavailable; using local fallback embeddings.",
                self.embedding_model,
            )
            return local_text_embedding(text, settings.embedding_dimensions)
        except RateLimitError as exc:
            raise AIRateLimitError() from exc
        except APITimeoutError as exc:
            raise AITimeoutError() from exc
        except Exception as exc:
            raise AIProviderError() from exc

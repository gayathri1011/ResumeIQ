"""AI provider protocol — swappable Groq, OpenAI, mock, etc."""

from typing import Protocol


class AIProviderProtocol(Protocol):
    async def complete(self, messages: list[dict[str, str]], **kwargs: object) -> str:
        """Return raw completion text from the provider."""

    async def embed(self, text: str) -> list[float]:
        """Return embedding vector for the given text."""

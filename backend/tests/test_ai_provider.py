"""Provider selection tests."""

from unittest.mock import patch

from app.ai.client import get_ai_provider
from app.ai.providers.groq_provider import GroqProvider
from app.ai.providers.mock_provider import MockAIProvider
from app.ai.providers.openai_provider import OpenAIProvider


def test_get_ai_provider_uses_groq_by_default(monkeypatch) -> None:
    monkeypatch.setattr("app.ai.client.settings.ai_mock_mode", False)
    monkeypatch.setattr("app.ai.client.settings.ai_provider", "groq")
    with patch("app.ai.providers.groq_provider.settings.ai_api_key", "gsk_test"):
        with patch("app.ai.providers.openai_provider.settings.ai_api_key", "gsk_test"):
            provider = get_ai_provider()
    assert isinstance(provider, GroqProvider)


def test_get_ai_provider_mock_mode(monkeypatch) -> None:
    monkeypatch.setattr("app.ai.client.settings.ai_mock_mode", True)
    assert isinstance(get_ai_provider(), MockAIProvider)


def test_get_ai_provider_openai_still_supported(monkeypatch) -> None:
    monkeypatch.setattr("app.ai.client.settings.ai_mock_mode", False)
    monkeypatch.setattr("app.ai.client.settings.ai_provider", "openai")
    with patch("app.ai.providers.openai_provider.settings.ai_api_key", "sk_test"):
        provider = get_ai_provider()
    assert isinstance(provider, OpenAIProvider)

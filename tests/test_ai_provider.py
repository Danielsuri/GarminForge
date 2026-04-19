# tests/test_ai_provider.py
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from web.ai_provider import ClaudeProvider, HuggingFaceProvider, get_ai_provider


VALID_PLAN = json.dumps({
    "days": [{"date": "2026-04-13", "meals": [
        {"type": "breakfast", "name": "Eggs", "kcal": 300,
         "macros": {"protein_g": 20, "carbs_g": 5, "fat_g": 18}}
    ]}],
    "groceries": [{"item": "Eggs", "qty": "12 pcs", "category": "protein"}],
    "reminders": [{"day": "2026-04-18", "text": "Prep veggies tonight"}],
})


def _hf_ok_response(content: str) -> MagicMock:
    """Build a mock httpx response matching the HF router (OpenAI-compatible) shape."""
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"choices": [{"message": {"content": content}}]}
    return mock


def test_huggingface_provider_returns_json() -> None:
    with patch("web.ai_provider.httpx.post", return_value=_hf_ok_response(f"```json\n{VALID_PLAN}\n```")):
        provider = HuggingFaceProvider(api_key="test-key", model="test-model")
        result = provider.complete("test prompt")

    data = json.loads(result)
    assert "days" in data
    assert "groceries" in data
    assert "reminders" in data


def test_huggingface_provider_retries_on_503() -> None:
    bad = MagicMock()
    bad.status_code = 503
    bad.text = "loading"

    with patch("web.ai_provider.httpx.post", side_effect=[bad, _hf_ok_response(VALID_PLAN)]):
        with patch("web.ai_provider.time.sleep"):
            provider = HuggingFaceProvider(api_key="test-key", model="test-model")
            result = provider.complete("test prompt")

    assert "days" in json.loads(result)


def test_get_ai_provider_returns_huggingface_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.setenv("HUGGINGFACE_API_KEY", "hf-test")
    provider = get_ai_provider()
    assert isinstance(provider, HuggingFaceProvider)


def test_get_ai_provider_returns_claude(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    provider = get_ai_provider()
    assert isinstance(provider, ClaudeProvider)

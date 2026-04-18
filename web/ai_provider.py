"""
Generic AI provider abstraction for GarminForge nutrition generation.

Switch providers via the AI_PROVIDER env var:
  AI_PROVIDER=huggingface  (default) — HuggingFace Inference API (free tier)
  AI_PROVIDER=claude                 — Anthropic claude-haiku-4-5-20251001
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from abc import ABC, abstractmethod

import httpx

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_DELAY = 2.0


class AIProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Call the AI with prompt; return validated JSON string."""
        ...


def _extract_json(text: str) -> str:
    """Strip markdown code fences and extract the first valid JSON object."""
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    for i, ch in enumerate(text):
        if ch in ("{", "["):
            depth = 0
            for j, c in enumerate(text[i:], i):
                if c in ("{", "["):
                    depth += 1
                elif c in ("}", "]"):
                    depth -= 1
                if depth == 0:
                    candidate = text[i : j + 1]
                    json.loads(candidate)  # raises ValueError if invalid
                    return candidate
    raise ValueError(f"No valid JSON in AI response: {text[:200]}")


class HuggingFaceProvider(AIProvider):
    def __init__(self, api_key: str, model: str = "mistralai/Mistral-7B-Instruct-v0.3") -> None:
        self._api_key = api_key
        self._model = model
        self._url = f"https://api-inference.huggingface.co/models/{model}"

    def complete(self, prompt: str) -> str:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload = {
            "inputs": prompt,
            "parameters": {"max_new_tokens": 2048, "temperature": 0.3, "return_full_text": False},
        }
        for attempt in range(_MAX_RETRIES):
            resp = httpx.post(self._url, headers=headers, json=payload, timeout=60.0)
            if resp.status_code == 503:
                logger.warning(
                    "HuggingFace 503 (model loading), retry %d/%d", attempt + 1, _MAX_RETRIES
                )
                time.sleep(_RETRY_DELAY * (attempt + 1))
                continue
            resp.raise_for_status()
            data = resp.json()
            raw: str = data[0]["generated_text"] if isinstance(data, list) else data["generated_text"]
            return _extract_json(raw)
        raise RuntimeError("HuggingFace provider failed after retries")


class ClaudeProvider(AIProvider):
    def __init__(self, api_key: str) -> None:
        import anthropic  # lazy — only needed when AI_PROVIDER=claude

        self._client = anthropic.Anthropic(api_key=api_key)

    def complete(self, prompt: str) -> str:
        import anthropic

        for attempt in range(_MAX_RETRIES):
            try:
                msg = self._client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=2048,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = msg.content[0].text  # type: ignore[union-attr]
                return _extract_json(raw)
            except anthropic.RateLimitError:
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_RETRY_DELAY * (attempt + 1))
                else:
                    raise
        raise RuntimeError("ClaudeProvider failed after retries")


def get_ai_provider() -> AIProvider:
    """Return the configured AI provider based on AI_PROVIDER env var."""
    name = os.environ.get("AI_PROVIDER", "huggingface").lower()
    if name == "claude":
        return ClaudeProvider(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    return HuggingFaceProvider(
        api_key=os.environ.get("HUGGINGFACE_API_KEY", ""),
        model=os.environ.get("HUGGINGFACE_MODEL", "mistralai/Mistral-7B-Instruct-v0.3"),
    )

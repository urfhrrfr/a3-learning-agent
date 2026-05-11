from __future__ import annotations

import os

import httpx

from .base import BaseLLMProvider, LLMProviderError


class OpenAICompatibleProvider(BaseLLMProvider):
    """Provider for OpenAI-compatible chat completion APIs."""

    name = "openai_compatible"

    def __init__(self) -> None:
        self.name = os.getenv("LLM_PROVIDER", self.name).strip().lower() or self.name
        self.api_key = os.getenv("OPENAI_COMPATIBLE_API_KEY", "")
        self.base_url = os.getenv("OPENAI_COMPATIBLE_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.getenv("OPENAI_COMPATIBLE_MODEL", "gpt-4o-mini")
        self.timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))

    def complete(self, prompt: str) -> str:
        if not self.api_key:
            raise LLMProviderError("OPENAI_COMPATIBLE_API_KEY is not configured")

        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "你是一个面向高校课程学习的教学资源生成助手。"},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.4,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            error_body = exc.response.text[:500]
            raise LLMProviderError(
                f"OpenAI-compatible provider request failed: {exc.response.status_code} {error_body}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"OpenAI-compatible provider request failed: {exc}") from exc

        payload = response.json()
        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError("OpenAI-compatible provider returned an unexpected response") from exc

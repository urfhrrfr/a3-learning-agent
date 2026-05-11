from __future__ import annotations

import os

from .base import BaseLLMProvider
from .mock_llm import MockLLMProvider
from .openai_compatible import OpenAICompatibleProvider
from .spark_llm import SparkLLMProvider


def get_llm_provider() -> BaseLLMProvider:
    provider = os.getenv("LLM_PROVIDER", "mock").strip().lower()
    if provider == "spark":
        return SparkLLMProvider()
    if provider in {"openai", "openai_compatible", "deepseek", "qwen", "dashscope"}:
        return OpenAICompatibleProvider()
    return MockLLMProvider()

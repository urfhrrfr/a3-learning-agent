from __future__ import annotations

import os

from .base import BaseEmbeddingProvider
from .mock_embedding import MockEmbeddingProvider


def get_embedding_provider() -> BaseEmbeddingProvider:
    provider = os.getenv("EMBEDDING_PROVIDER", "mock").strip().lower()
    if provider == "mock":
        return MockEmbeddingProvider()
    raise RuntimeError(f"Embedding provider '{provider}' is reserved but not implemented yet")

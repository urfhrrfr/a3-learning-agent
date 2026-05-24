from __future__ import annotations

import os

from .base import BaseVectorStore
from .memory_store import MemoryVectorStore


def vector_store_provider() -> str:
    return os.getenv("VECTOR_STORE", os.getenv("VECTOR_STORE_PROVIDER", "memory")).strip().lower()


def get_vector_store(collection_name: str = "course") -> BaseVectorStore:
    provider = vector_store_provider()
    if provider == "memory":
        return MemoryVectorStore()
    if provider == "chroma":
        try:
            from .chroma_store import ChromaVectorStore

            return ChromaVectorStore(collection_name=collection_name)
        except Exception:
            return MemoryVectorStore()
    raise RuntimeError(f"Vector store provider '{provider}' is not implemented")


def vector_store_status(collection_name: str = "course") -> dict:
    requested = vector_store_provider()
    store = get_vector_store(collection_name=collection_name)
    return {
        "requested": requested,
        "active": store.name,
        "fallback": requested != store.name,
        "collection": getattr(store, "collection_name", collection_name),
        "persist_dir": getattr(store, "persist_dir", None),
    }

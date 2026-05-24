from __future__ import annotations

import os
import re
from typing import Any

from .base import BaseVectorStore, VectorRecord, VectorSearchResult


class ChromaVectorStore(BaseVectorStore):
    name = "chroma"

    def __init__(self, collection_name: str = "course", persist_dir: str | None = None):
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError("chromadb package is not installed") from exc

        self.collection_name = self._normalize_collection_name(collection_name)
        self.persist_dir = persist_dir or os.getenv("CHROMA_PERSIST_DIR", ".chroma")
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(name=self.collection_name)

    def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        self.collection.upsert(
            ids=[record.id for record in records],
            embeddings=[record.vector for record in records],
            documents=[record.document for record in records],
            metadatas=[self._metadata(record) for record in records],
        )

    def search(
        self,
        query_vector: list[float],
        *,
        top_k: int = 5,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        where = self._clean_metadata(metadata_filter or {}) or None
        result = self.collection.query(
            query_embeddings=[query_vector],
            n_results=max(1, top_k),
            where=where,
            include=["documents", "metadatas", "distances", "embeddings"],
        )
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        embeddings = result.get("embeddings", [[]])[0]

        matches: list[VectorSearchResult] = []
        for index, record_id in enumerate(ids):
            distance = float(distances[index]) if index < len(distances) else 1.0
            vector = embeddings[index] if index < len(embeddings) and embeddings[index] is not None else []
            matches.append(
                VectorSearchResult(
                    record=VectorRecord(
                        id=str(record_id),
                        vector=list(vector),
                        document=str(documents[index]) if index < len(documents) and documents[index] else "",
                        metadata=dict(metadatas[index] or {}) if index < len(metadatas) else {},
                    ),
                    score=max(0.0, min(1.0, 1.0 / (1.0 + max(0.0, distance)))),
                )
            )
        return matches

    @staticmethod
    def _metadata(record: VectorRecord) -> dict[str, Any]:
        metadata = {
            "chunk_id": record.id,
            "chapter_id": record.metadata.get("chapter_id", ""),
            "section": record.metadata.get("section", ""),
            "difficulty": record.metadata.get("difficulty", ""),
            "source_type": record.metadata.get("source_type", ""),
        }
        return ChromaVectorStore._clean_metadata(metadata)

    @staticmethod
    def _clean_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in metadata.items()
            if isinstance(value, str | int | float | bool) and value is not None
        }

    @staticmethod
    def _normalize_collection_name(collection_name: str) -> str:
        normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", collection_name.strip())[:63]
        normalized = normalized.strip("._-")
        if len(normalized) < 3:
            return "course"
        return normalized

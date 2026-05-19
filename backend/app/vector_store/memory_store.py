from __future__ import annotations

import math
from typing import Any

from .base import BaseVectorStore, VectorRecord, VectorSearchResult


class MemoryVectorStore(BaseVectorStore):
    """Small in-process vector store used before wiring a real database."""

    name = "memory"

    def __init__(self):
        self.records: dict[str, VectorRecord] = {}

    def upsert(self, records: list[VectorRecord]) -> None:
        for record in records:
            self.records[record.id] = record

    def search(
        self,
        query_vector: list[float],
        *,
        top_k: int = 5,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        results: list[VectorSearchResult] = []
        for record in self.records.values():
            if metadata_filter and not self._metadata_matches(record.metadata, metadata_filter):
                continue
            results.append(VectorSearchResult(record=record, score=self._cosine(query_vector, record.vector)))
        return sorted(results, key=lambda item: item.score, reverse=True)[:top_k]

    @staticmethod
    def _metadata_matches(metadata: dict[str, Any], expected: dict[str, Any]) -> bool:
        return all(metadata.get(key) == value for key, value in expected.items())

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        dot = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return max(0.0, min(1.0, dot / (left_norm * right_norm)))

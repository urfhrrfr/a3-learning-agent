from __future__ import annotations

from app.embedding import BaseEmbeddingProvider
from app.vector_store import BaseVectorStore

from .indexer import CourseVectorIndex, build_course_vector_index


class VectorRetriever:
    def __init__(
        self,
        course: dict,
        *,
        embedding: BaseEmbeddingProvider | None = None,
        store: BaseVectorStore | None = None,
        index: CourseVectorIndex | None = None,
        top_k: int = 5,
    ):
        self.index = index or build_course_vector_index(course, embedding=embedding, store=store)
        self.top_k = top_k

    @staticmethod
    def profile_boost(chunk, current_chapter_id: str, preferred_sections: set[str] | None = None) -> float:
        boost = 0.0
        if current_chapter_id and chunk.chapter_id == current_chapter_id:
            boost += 0.12
        if preferred_sections and chunk.section in preferred_sections:
            boost += 0.08
        return boost

    def retrieve_candidates(
        self,
        *,
        query: str,
        profile_context: str,
        current_chapter_id: str = "",
        preferred_sections: set[str] | None = None,
        max_candidates: int | None = None,
    ) -> list[dict]:
        query_vector = self.index.embedding.embed_text(f"{query}\n{profile_context}")
        limit = max_candidates or self.top_k
        results = self.index.store.search(query_vector, top_k=len(self.index.chunks))
        chunks_by_id = self.index.chunks_by_id

        candidates: list[dict] = []
        for result in results:
            chunk = chunks_by_id.get(result.record.id)
            if chunk is None:
                continue
            vector_score = float(result.score)
            profile_boost = self.profile_boost(chunk, current_chapter_id, preferred_sections)
            final_score = min(1.0, vector_score + profile_boost)
            candidates.append(
                {
                    "chunk": chunk,
                    "score": final_score,
                    "vector_score": vector_score,
                    "profile_boost": profile_boost,
                    "final_score": final_score,
                    "retrieval_channels": ["vector"],
                    "reason": "Vector similarity over course chunks, profile context, chapter and resource preferences.",
                }
            )
        return sorted(candidates, key=lambda item: item["final_score"], reverse=True)[:limit]

    def retrieve(
        self,
        *,
        query: str,
        profile_context: str,
        current_chapter_id: str = "",
        preferred_sections: set[str] | None = None,
    ) -> list[dict]:
        return [
            self._candidate_as_source(item)
            for item in self.retrieve_candidates(
                query=query,
                profile_context=profile_context,
                current_chapter_id=current_chapter_id,
                preferred_sections=preferred_sections,
                max_candidates=self.top_k,
            )
        ]

    @staticmethod
    def _candidate_as_source(candidate: dict) -> dict:
        source = candidate["chunk"].as_source(candidate["final_score"], candidate["reason"])
        source.update(
            {
                "vector_score": round(float(candidate.get("vector_score", 0.0)), 2),
                "profile_boost": round(float(candidate.get("profile_boost", 0.0)), 2),
                "final_score": round(float(candidate.get("final_score", 0.0)), 2),
                "retrieval_channels": list(candidate.get("retrieval_channels", [])),
            }
        )
        return source

from __future__ import annotations

import json
import re
from typing import Protocol

from .chunk_builder import build_course_chunks
from .lexical_retriever import LexicalRetriever
from .vector_retriever import VectorRetriever


class CompletesText(Protocol):
    name: str

    def complete(self, prompt: str) -> str:
        ...


class HybridRetriever:
    def __init__(
        self,
        course: dict,
        *,
        llm: CompletesText | None = None,
        max_candidates: int = 12,
        top_k: int = 5,
    ):
        self.course = course
        self.llm = llm
        self.max_candidates = max_candidates
        self.top_k = top_k
        self.chunks = build_course_chunks(course)
        self.lexical = LexicalRetriever(self.chunks)
        self.vector = VectorRetriever(course, top_k=max_candidates)

    @staticmethod
    def parse_json(content: str):
        cleaned = content.strip()
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if fence_match:
            cleaned = fence_match.group(1).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("[")
            end = cleaned.rfind("]")
            if start != -1 and end != -1 and end > start:
                return json.loads(cleaned[start : end + 1])
            raise

    @staticmethod
    def profile_boost(chunk, current_chapter_id: str, preferred_sections: set[str] | None = None) -> float:
        boost = 0.0
        if current_chapter_id and chunk.chapter_id == current_chapter_id:
            boost += 0.12
        if preferred_sections and chunk.section in preferred_sections:
            boost += 0.08
        if chunk.section in {"misconceptions", "difficulties", "practice_questions", "code_labs"}:
            boost += 0.05
        return min(0.25, boost)

    @staticmethod
    def candidate_as_source(candidate: dict, relevance_score: float, reason: str) -> dict:
        source = candidate["chunk"].as_source(relevance_score, reason)
        source.update(
            {
                "lexical_score": round(float(candidate.get("lexical_score", 0.0)), 2),
                "vector_score": round(float(candidate.get("vector_score", 0.0)), 2),
                "profile_boost": round(float(candidate.get("profile_boost", 0.0)), 2),
                "final_score": round(float(candidate.get("final_score", 0.0)), 2),
                "retrieval_channels": list(candidate.get("retrieval_channels", [])),
            }
        )
        return source

    def merge_candidates(
        self,
        lexical_candidates: list[dict],
        vector_candidates: list[dict],
        *,
        current_chapter_id: str,
        preferred_sections: set[str] | None = None,
    ) -> list[dict]:
        merged: dict[str, dict] = {}

        def ensure_candidate(chunk):
            if chunk.id not in merged:
                merged[chunk.id] = {
                    "chunk": chunk,
                    "lexical_score": 0.0,
                    "vector_score": 0.0,
                    "profile_boost": self.profile_boost(chunk, current_chapter_id, preferred_sections),
                    "final_score": 0.0,
                    "score": 0.0,
                    "retrieval_channels": [],
                    "reason": "",
                }
            return merged[chunk.id]

        for item in lexical_candidates:
            candidate = ensure_candidate(item["chunk"])
            candidate["lexical_score"] = max(candidate["lexical_score"], float(item.get("score", 0.0)))
            if "lexical" not in candidate["retrieval_channels"]:
                candidate["retrieval_channels"].append("lexical")

        for item in vector_candidates:
            candidate = ensure_candidate(item["chunk"])
            candidate["vector_score"] = max(candidate["vector_score"], float(item.get("vector_score", item.get("score", 0.0))))
            if "vector" not in candidate["retrieval_channels"]:
                candidate["retrieval_channels"].append("vector")

        for candidate in merged.values():
            lexical_score = candidate["lexical_score"]
            vector_score = candidate["vector_score"]
            if lexical_score and vector_score:
                base_score = lexical_score * 0.5 + vector_score * 0.5
                reason = "Lexical and vector retrieval both matched this course chunk."
            elif lexical_score:
                base_score = lexical_score
                reason = "Lexical retrieval matched this course chunk."
            else:
                base_score = vector_score
                reason = "Vector retrieval matched this course chunk."
            candidate["final_score"] = min(1.0, base_score + candidate["profile_boost"])
            candidate["score"] = candidate["final_score"]
            candidate["reason"] = reason

        return sorted(merged.values(), key=lambda item: item["final_score"], reverse=True)[: self.max_candidates]

    def build_rerank_prompt(self, query: str, profile_context: str, candidates: list[dict]) -> str:
        candidate_text = "\n\n".join(
            (
                f"[{idx}] id={item['chunk'].id}\n"
                f"chapter={item['chunk'].chapter_title}; section={item['chunk'].section_label}\n"
                f"scores lexical={item.get('lexical_score', 0.0):.2f}, "
                f"vector={item.get('vector_score', 0.0):.2f}, "
                f"profile_boost={item.get('profile_boost', 0.0):.2f}, "
                f"final={item.get('final_score', item.get('score', 0.0)):.2f}, "
                f"channels={','.join(item.get('retrieval_channels', []))}\n"
                f"text={item['chunk'].text}"
            )
            for idx, item in enumerate(candidates, start=1)
        )
        return f"""You are a course knowledge reranker. Select the 3-5 most useful chunks for the current user query and student profile.
Ranking criteria:
1. Directly supports the user query.
2. Covers weak points and mistake patterns from the profile.
3. Prefer chunks that can ground explanations, practice, or code labs.
4. Do not invent ids outside the candidate list.

User query:
{query}

Student profile:
{profile_context}

Candidate chunks:
{candidate_text}

Return only a JSON array:
[{{"id": "candidate chunk id", "relevance_score": 0.0, "reason": "short reason"}}]
"""

    def normalize_rerank_result(self, raw_result, candidates: list[dict]) -> list[dict]:
        candidates_by_id = {item["chunk"].id: item for item in candidates}
        raw_items = raw_result.get("results", []) if isinstance(raw_result, dict) else raw_result
        if not isinstance(raw_items, list):
            return []

        selected: list[dict] = []
        seen: set[str] = set()
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            chunk_id = str(item.get("id", ""))
            if chunk_id not in candidates_by_id or chunk_id in seen:
                continue
            try:
                score = float(item.get("relevance_score", candidates_by_id[chunk_id]["final_score"]))
            except (TypeError, ValueError):
                score = float(candidates_by_id[chunk_id]["final_score"])
            selected.append(
                self.candidate_as_source(
                    candidates_by_id[chunk_id],
                    score,
                    str(item.get("reason", "LLM rerank selected this chunk.")),
                )
            )
            seen.add(chunk_id)
            if len(selected) >= self.top_k:
                break
        return selected

    def fallback_rerank(self, candidates: list[dict]) -> list[dict]:
        return [
            self.candidate_as_source(item, item["final_score"], item["reason"])
            for item in sorted(candidates, key=lambda candidate: candidate["final_score"], reverse=True)[: self.top_k]
        ]

    def retrieve(
        self,
        *,
        query: str,
        profile_context: str,
        current_chapter_id: str,
        preferred_sections: set[str] | None = None,
    ) -> tuple[list[dict], list[str]]:
        warnings: list[str] = []
        lexical_candidates = self.lexical.retrieve(
            query,
            profile_context,
            current_chapter_id,
            preferred_sections=preferred_sections,
            max_candidates=self.max_candidates,
        )

        try:
            vector_candidates = self.vector.retrieve_candidates(
                query=query,
                profile_context=profile_context,
                current_chapter_id=current_chapter_id,
                preferred_sections=preferred_sections,
                max_candidates=len(self.chunks),
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"Vector retrieval unavailable, used lexical fallback: {exc}")
            vector_candidates = []

        candidates = self.merge_candidates(
            lexical_candidates,
            vector_candidates,
            current_chapter_id=current_chapter_id,
            preferred_sections=preferred_sections,
        )

        selected: list[dict] = []
        if self.llm and getattr(self.llm, "name", "") != "mock":
            try:
                prompt = self.build_rerank_prompt(query, profile_context, candidates)
                selected = self.normalize_rerank_result(self.parse_json(self.llm.complete(prompt)), candidates)
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"LLM rerank unavailable, used local hybrid retrieval: {exc}")

        if not selected:
            selected = self.fallback_rerank(candidates)
        return selected, warnings

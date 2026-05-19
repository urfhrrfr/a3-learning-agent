from __future__ import annotations

import re

from .chunk_schema import KnowledgeChunk


STOP_WORDS = {"学习", "目标", "当前", "章节", "知识", "理解", "掌握", "案例", "资源", "生成"}


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{2,}", text.lower())
    return [token for token in tokens if token not in STOP_WORDS]


class LexicalRetriever:
    def __init__(self, chunks: list[KnowledgeChunk]):
        self.chunks = chunks

    def score(
        self,
        chunk: KnowledgeChunk,
        query: str,
        profile_context: str,
        current_chapter_id: str,
        preferred_sections: set[str] | None = None,
    ) -> float:
        intent_tokens = set(tokenize(f"{query}\n{profile_context}"))
        chunk_tokens = set(tokenize(f"{chunk.chapter_title} {chunk.section_label} {chunk.text} {' '.join(chunk.keywords)}"))
        if not intent_tokens:
            overlap = 0.0
        else:
            overlap = len(intent_tokens & chunk_tokens) / max(len(intent_tokens), 1)
        chapter_boost = 0.2 if chunk.chapter_id == current_chapter_id else 0.0
        weakness_boost = 0.15 if any(token in chunk.text.lower() for token in intent_tokens) else 0.0
        section_boost = 0.12 if preferred_sections and chunk.section in preferred_sections else 0.0
        evidence_boost = 0.08 if chunk.section in {"misconceptions", "difficulties", "practice_questions", "code_labs"} else 0.0
        return min(1.0, 0.2 + overlap + chapter_boost + weakness_boost + section_boost + evidence_boost)

    def retrieve(
        self,
        query: str,
        profile_context: str,
        current_chapter_id: str,
        *,
        preferred_sections: set[str] | None = None,
        max_candidates: int = 12,
    ) -> list[dict]:
        scored = []
        for chunk in self.chunks:
            score = self.score(chunk, query, profile_context, current_chapter_id, preferred_sections)
            scored.append(
                {
                    "chunk": chunk,
                    "score": score,
                    "reason": "关键词、章节、学生画像和资源类型综合召回。",
                }
            )
        return sorted(scored, key=lambda item: item["score"], reverse=True)[:max_candidates]

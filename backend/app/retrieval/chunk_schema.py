from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class KnowledgeChunk:
    id: str
    course_id: str
    chapter_id: str
    chapter_title: str
    section: str
    section_label: str
    text: str
    keywords: tuple[str, ...] = field(default_factory=tuple)
    difficulty: str = "基础"
    source_type: str = "course"

    def as_source(self, relevance_score: float = 0.0, reason: str = "") -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "relevance_score": round(min(max(float(relevance_score), 0.0), 1.0), 2),
            "chapter_title": self.chapter_title,
            "section": self.section,
            "section_label": self.section_label,
            "keywords": list(self.keywords),
            "difficulty": self.difficulty,
            "source_type": self.source_type,
            "reason": reason,
        }

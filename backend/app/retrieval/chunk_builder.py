from __future__ import annotations

import re
from typing import Any

from .chunk_schema import KnowledgeChunk


SECTION_LABELS = {
    "objectives": "学习目标",
    "concept_cards": "概念卡片",
    "detailed_concepts": "详细知识点",
    "difficulties": "学习难点",
    "misconceptions": "常见误区",
    "real_cases": "真实案例",
    "code_labs": "代码实验",
    "practice_questions": "练习题",
    "reading": "拓展阅读",
    "task": "实践任务",
}


DIFFICULTY_BY_SECTION = {
    "objectives": "基础",
    "concept_cards": "基础",
    "detailed_concepts": "基础到应用",
    "difficulties": "应用",
    "misconceptions": "应用",
    "real_cases": "综合",
    "code_labs": "实践",
    "practice_questions": "练习",
    "reading": "拓展",
    "task": "实践",
}


def stringify_item(item: Any) -> str:
    if isinstance(item, dict):
        parts: list[str] = []
        for key in [
            "name",
            "definition",
            "why_it_matters",
            "example",
            "check_question",
            "stem",
            "standard_answer",
            "explanation",
            "assessment_point",
            "title",
        ]:
            value = item.get(key)
            if value:
                parts.append(str(value))
        if item.get("rubric"):
            parts.append("评价标准：" + "；".join(str(value) for value in item["rubric"]))
        if item.get("options"):
            parts.append("选项：" + "；".join(str(value) for value in item["options"]))
        return "；".join(parts)
    return str(item)


def extract_keywords(text: str, chapter_title: str, section_label: str) -> tuple[str, ...]:
    tokens = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{2,}", f"{chapter_title} {section_label} {text}".lower())
    stop_words = {
        "学习",
        "目标",
        "当前",
        "章节",
        "知识",
        "理解",
        "掌握",
        "案例",
        "能够",
        "说明",
        "进行",
    }
    seen: set[str] = set()
    keywords: list[str] = []
    for token in tokens:
        if token in stop_words or token in seen:
            continue
        seen.add(token)
        keywords.append(token)
        if len(keywords) >= 12:
            break
    return tuple(keywords)


def build_course_chunks(course: dict) -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    course_id = str(course.get("id", "course"))
    for chapter in course.get("chapters", []):
        chapter_id = str(chapter["id"])
        chapter_title = str(chapter["title"])
        for section, section_label in SECTION_LABELS.items():
            raw_value = chapter.get(section)
            if not raw_value:
                continue
            items = raw_value if isinstance(raw_value, list) else [raw_value]
            for index, item in enumerate(items, start=1):
                text = re.sub(r"\s+", " ", stringify_item(item)).strip()
                if not text:
                    continue
                chunks.append(
                    KnowledgeChunk(
                        id=f"{chapter_id}#{section}:{index:02d}",
                        course_id=course_id,
                        chapter_id=chapter_id,
                        chapter_title=chapter_title,
                        section=section,
                        section_label=section_label,
                        text=text,
                        keywords=extract_keywords(text, chapter_title, section_label),
                        difficulty=DIFFICULTY_BY_SECTION.get(section, "基础"),
                    )
                )
    return chunks

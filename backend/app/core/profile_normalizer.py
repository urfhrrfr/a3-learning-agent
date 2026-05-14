from __future__ import annotations

import re
from collections.abc import Iterable, Mapping


class ProfileNormalizer:
    """Normalize learning-profile tags into stable canonical labels.

    The normalizer owns vocabulary-level cleanup so agents can focus on
    extraction and reasoning. It currently uses static aliases and exposes
    `load_from_course_knowledge()` as the future extension point for loading
    canonical concepts from the course knowledge base.
    """

    DEFAULT_ALIASES: dict[str, str] = {
        "python": "Python",
        "python基础": "Python",
        "python基础扎实": "Python",
        "python代码": "代码案例",
        "python代码案例": "代码案例",
        "代码": "代码案例",
        "代码例子": "代码案例",
        "代码案例": "代码案例",
        "案例": "案例",
        "例子": "案例",
        "图": "图解",
        "图解": "图解",
        "视频": "短视频",
        "短视频": "短视频",
        "动画": "短视频",
        "阅读": "阅读材料",
        "阅读材料": "阅读材料",
        "书": "阅读材料",
        "高数": "高等数学",
        "高等数学": "高等数学",
        "线代": "线性代数",
        "线性代数": "线性代数",
        "线性代数薄弱": "线性代数薄弱",
        "线代薄弱": "线性代数薄弱",
        "概率": "概率论",
        "概率论": "概率论",
        "梯度": "梯度下降",
        "梯度下降": "梯度下降",
        "评估": "模型评估指标",
        "指标": "模型评估指标",
        "评估指标": "模型评估指标",
        "模型评估指标": "模型评估指标",
        "反向": "反向传播",
        "反向传播": "反向传播",
        "过拟合": "过拟合",
        "泛化": "泛化能力",
        "泛化能力": "泛化能力",
        "概念混淆": "概念混淆",
        "混淆": "概念混淆",
        "迁移": "知识迁移困难",
        "知识迁移困难": "知识迁移困难",
        "公式": "公式不会迁移",
        "公式不会迁移": "公式不会迁移",
        "术语": "只记术语不会应用",
        "只记术语不会应用": "只记术语不会应用",
        "教育": "智能教育",
        "智能教育": "智能教育",
        "机器学习": "机器学习应用",
        "机器学习应用": "机器学习应用",
        "视觉": "计算机视觉",
        "计算机视觉": "计算机视觉",
        "nlp": "自然语言处理",
        "自然语言": "自然语言处理",
        "自然语言处理": "自然语言处理",
    }

    def __init__(self, alias_map: Mapping[str, str] | None = None):
        self.alias_map = self._build_alias_map(alias_map or self.DEFAULT_ALIASES)
        self.course_concepts: set[str] = set()

    def _build_alias_map(self, alias_map: Mapping[str, str]) -> dict[str, str]:
        return {self._key(alias): canonical.strip() for alias, canonical in alias_map.items() if alias and canonical}

    def _key(self, value: str) -> str:
        return re.sub(r"\s+", "", str(value).strip()).lower()

    def _clean(self, value: str) -> str:
        return re.sub(r"\s+", "", str(value).strip())

    def load_from_course_knowledge(self, course_knowledge: Mapping | None = None) -> None:
        """Load canonical concepts from course knowledge.

        This is intentionally small today. Future versions can read the course
        file/chapter schema and extend alias maps with domain concepts from it.
        """
        if not course_knowledge:
            return

        concepts: set[str] = set()
        chapters = course_knowledge.get("chapters", []) if isinstance(course_knowledge, Mapping) else []
        for chapter in chapters:
            if not isinstance(chapter, Mapping):
                continue
            for key in ("concepts", "detailed_concepts"):
                for item in self._iter_text_items(chapter.get(key, [])):
                    concepts.add(item)

        self.course_concepts.update(concepts)
        self.alias_map.update({self._key(concept): concept for concept in concepts})

    def _iter_text_items(self, values: Iterable) -> Iterable[str]:
        for item in values:
            if isinstance(item, str):
                text = item.strip()
            elif isinstance(item, Mapping):
                text = str(item.get("name") or item.get("title") or item.get("concept") or "").strip()
            else:
                text = ""
            if text:
                yield text

    def normalize_tag(self, tag: str) -> str:
        cleaned = self._clean(tag)
        if not cleaned:
            return ""
        return self.alias_map.get(self._key(cleaned), cleaned)

    def normalize_tags(self, tags: list[str]) -> list[str]:
        """Normalize tag casing, whitespace, aliases, and duplicates."""
        normalized: list[str] = []
        seen: set[str] = set()
        for tag in tags:
            canonical = self.normalize_tag(tag)
            key = self._key(canonical)
            if key and key not in seen:
                seen.add(key)
                normalized.append(canonical)
        return normalized

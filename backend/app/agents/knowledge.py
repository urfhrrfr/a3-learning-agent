from __future__ import annotations

import json
import re
from html import escape
from uuid import uuid4

from .base import Agent, WorkflowState, bullets, now, parse_llm_json
from ..assessment_prompts import build_assessment_prompt, build_review_fact_check_prompt
from ..core.profile_normalizer import ProfileNormalizer
from ..core.profile_validator import ProfileValidator
from ..knowledge import COURSE, find_chapter
from ..providers.base import BaseLLMProvider, LLMProviderError
from ..providers.factory import get_llm_provider
from ..prompts import (
    build_profile_extraction_prompt,
    build_profile_semantic_fusion_prompt,
)
from ..pptx_renderer import PPTXRenderError, render_pptx_deck
from ..retrieval import HybridRetriever, save_retrieval_log
from ..schemas import AgentTrace, GenerateRequest, Profile, Resource


class KnowledgeAgent(Agent):
    name = "KnowledgeAgent"
    role = "检索课程知识库"
    stage = "knowledge"
    boundary = "只负责检索与证据整理，不直接生成学习资源"
    depends_on = ["ProfileAgent"]
    max_candidates = 12
    top_k = 5
    preferred_sections_by_resource_type = {
        "lecture_doc": {"objectives", "concept_cards", "detailed_concepts", "difficulties", "misconceptions", "real_cases"},
        "mind_map": {"objectives", "concept_cards", "detailed_concepts", "misconceptions"},
        "quiz": {"practice_questions", "detailed_concepts", "misconceptions"},
        "reading": {"reading", "real_cases", "code_labs", "difficulties"},
        "media_script": {"real_cases", "misconceptions", "detailed_concepts"},
        "animation_demo": {"detailed_concepts", "misconceptions", "real_cases"},
        "html_ppt": {"objectives", "detailed_concepts", "real_cases"},
        "visual_card": {"concept_cards", "detailed_concepts", "misconceptions", "practice_questions"},
        "code_case": {"code_labs", "real_cases", "detailed_concepts"},
    }

    section_labels = {
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

    def _current_query(self, state: WorkflowState) -> str:
        explicit_query = getattr(state, "current_query", "") or getattr(state.request, "current_query", "")
        if explicit_query:
            return str(explicit_query)
        pain_points = "、".join(state.request.pain_points or [])
        return f"{state.request.chapter}；学习目标：{state.request.goal}；当前困惑：{pain_points}".strip("；")

    @staticmethod
    def _stringify_item(item) -> str:
        if isinstance(item, dict):
            parts = []
            for key in ["name", "definition", "why_it_matters", "example", "check_question", "stem", "standard_answer", "explanation", "assessment_point"]:
                value = item.get(key)
                if value:
                    parts.append(str(value))
            if item.get("rubric"):
                parts.append("评价标准：" + "；".join(str(value) for value in item["rubric"]))
            return "；".join(parts)
        return str(item)

    def _candidate_fragments(self, state: WorkflowState) -> list[dict]:
        candidates: list[dict] = []
        for chapter in COURSE["chapters"]:
            for section, label in self.section_labels.items():
                raw_value = chapter.get(section)
                if not raw_value:
                    continue
                items = raw_value if isinstance(raw_value, list) else [raw_value]
                for index, item in enumerate(items, start=1):
                    text = self._stringify_item(item)
                    if not text:
                        continue
                    candidates.append(
                        {
                            "id": f"{chapter['id']}#{section}:{index:02d}",
                            "chapter_id": chapter["id"],
                            "chapter_title": chapter["title"],
                            "section": section,
                            "section_label": label,
                            "text": text,
                        }
                    )
        return candidates

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        tokens = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{2,}", text.lower())
        stop_words = {"学习", "目标", "当前", "章节", "知识", "理解", "掌握", "案例"}
        return [token for token in tokens if token not in stop_words]

    def _profile_context(self, state: WorkflowState) -> str:
        profile = state.profile
        weak_points = "、".join(getattr(profile, "weak_points", []) or [])
        mistake_patterns = "、".join(getattr(profile, "mistake_patterns", []) or [])
        knowledge_base = "、".join(getattr(profile, "knowledge_base", []) or [])
        return (
            f"学习目标：{getattr(profile, 'learning_goal', '')}\n"
            f"薄弱点：{weak_points}\n"
            f"常见错误模式：{mistake_patterns}\n"
            f"已有基础：{knowledge_base}\n"
            f"偏好：{getattr(profile, 'cognitive_style', '')}，{'、'.join(getattr(profile, 'preferred_modalities', []) or [])}"
        )

    def _lexical_score(self, fragment: dict, query: str, profile_context: str, current_chapter_id: str) -> float:
        intent_tokens = set(self._tokenize(f"{query}\n{profile_context}"))
        fragment_tokens = set(self._tokenize(f"{fragment['chapter_title']} {fragment['section_label']} {fragment['text']}"))
        if not intent_tokens:
            return 0.2
        overlap = len(intent_tokens & fragment_tokens) / max(len(intent_tokens), 1)
        chapter_boost = 0.2 if fragment["chapter_id"] == current_chapter_id else 0.0
        weakness_boost = 0.15 if any(token in fragment["text"].lower() for token in intent_tokens) else 0.0
        section_boost = 0.1 if fragment["section"] in {"misconceptions", "difficulties", "practice_questions", "code_labs"} else 0.0
        return min(1.0, 0.2 + overlap + chapter_boost + weakness_boost + section_boost)

    def _prefilter_candidates(self, state: WorkflowState, query: str, profile_context: str) -> list[dict]:
        candidates = self._candidate_fragments(state)
        for candidate in candidates:
            candidate["_prefilter_score"] = self._lexical_score(candidate, query, profile_context, state.chapter["id"])
        return sorted(candidates, key=lambda item: item["_prefilter_score"], reverse=True)[: self.max_candidates]

    def _build_rerank_prompt(self, query: str, profile_context: str, candidates: list[dict]) -> str:
        candidate_text = "\n\n".join(
            (
                f"[{idx}] id={item['id']}\n"
                f"章节={item['chapter_title']}；类型={item['section_label']}\n"
                f"片段={item['text']}"
            )
            for idx, item in enumerate(candidates, start=1)
        )
        return f"""你是课程知识库的相关性裁判（Reranker）。
请根据“用户当前提问”和“学生画像”从候选知识片段中挑出最应该召回的 3-5 个片段。

排序标准：
1. 直接回答用户当前提问。
2. 优先覆盖学生薄弱点和常见错误模式。
3. 优先选择可支撑后续讲解、练习或代码实验的片段。
4. 不要编造候选列表外的 id。

用户当前提问：
{query}

学生画像：
{profile_context}

候选知识片段：
{candidate_text}

只输出 JSON 数组，每个元素格式如下：
{{"id": "候选片段 id", "relevance_score": 0.0, "reason": "一句话说明为什么相关"}}
"""

    def _normalize_rerank_result(self, raw_result, candidates_by_id: dict[str, dict]) -> list[dict]:
        if isinstance(raw_result, dict):
            raw_items = raw_result.get("results", [])
        elif isinstance(raw_result, list):
            raw_items = raw_result
        else:
            raw_items = []

        selected: list[dict] = []
        seen: set[str] = set()
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            fragment_id = str(item.get("id", ""))
            if fragment_id not in candidates_by_id or fragment_id in seen:
                continue
            try:
                score = float(item.get("relevance_score", 0.0))
            except (TypeError, ValueError):
                score = 0.0
            fragment = candidates_by_id[fragment_id]
            selected.append(
                {
                    "id": fragment_id,
                    "text": fragment["text"],
                    "relevance_score": round(min(max(score, 0.0), 1.0), 2),
                    "chapter_title": fragment["chapter_title"],
                    "section": fragment["section"],
                    "reason": str(item.get("reason", "")),
                }
            )
            seen.add(fragment_id)
            if len(selected) >= self.top_k:
                break
        return selected

    def _fallback_rerank(self, candidates: list[dict]) -> list[dict]:
        selected = []
        for item in sorted(candidates, key=lambda candidate: candidate.get("_prefilter_score", 0), reverse=True)[: self.top_k]:
            selected.append(
                {
                    "id": item["id"],
                    "text": item["text"],
                    "relevance_score": round(float(item.get("_prefilter_score", 0.5)), 2),
                    "chapter_title": item["chapter_title"],
                    "section": item["section"],
                    "reason": "基于当前提问、薄弱点与章节关键词的轻量规则排序命中。",
                }
            )
        return selected

    def _preferred_sections(self, state: WorkflowState) -> set[str]:
        sections: set[str] = set()
        requested_types = state.request.resource_types or []
        for resource_type in requested_types:
            sections.update(self.preferred_sections_by_resource_type.get(resource_type, set()))
        return sections

    def run(self, state: WorkflowState) -> dict:
        query = self._current_query(state)
        profile_context = self._profile_context(state)
        retriever = HybridRetriever(COURSE, llm=self.llm, max_candidates=self.max_candidates, top_k=self.top_k)
        selected, warnings = retriever.retrieve(
            query=query,
            profile_context=profile_context,
            current_chapter_id=state.chapter["id"],
            preferred_sections=self._preferred_sections(state),
        )

        state.sources = selected
        save_retrieval_log(
            scenario="resource_generation",
            job_id=state.job_id,
            query=query,
            profile_snapshot=state.profile.model_dump(),
            selected_sources=selected,
            request_context={
                "course": state.request.course,
                "chapter": state.request.chapter,
                "goal": state.request.goal,
                "pain_points": state.request.pain_points,
                "resource_types": state.request.resource_types,
                "target_concepts": state.request.target_concepts,
                "raw_user_need": state.request.raw_user_need,
                "chapter_match_confidence": state.request.chapter_match_confidence,
                "current_chapter_id": state.chapter["id"],
            },
            warnings=warnings,
        )
        avg_score = sum(item["relevance_score"] for item in selected) / max(len(selected), 1)
        return {
            "summary": f"语义检索到 {len(selected)} 个与“{query}”最相关的课程知识片段（RAG）",
            "confidence": round(avg_score, 2),
            "warnings": warnings,
        }

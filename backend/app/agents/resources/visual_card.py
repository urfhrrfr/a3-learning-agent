from __future__ import annotations

import json
import re
from html import escape
from uuid import uuid4

from ..base import Agent, WorkflowState, bullets, now, parse_llm_json
from ...assessment_prompts import build_assessment_prompt, build_review_fact_check_prompt
from ...core.profile_normalizer import ProfileNormalizer
from ...core.profile_validator import ProfileValidator
from ...knowledge import COURSE, find_chapter
from ...providers.base import BaseLLMProvider, LLMProviderError
from ...providers.factory import get_llm_provider
from ...prompts import (
    build_profile_extraction_prompt,
    build_profile_semantic_fusion_prompt,
)
from ...pptx_renderer import PPTXRenderError, render_pptx_deck
from ...retrieval import HybridRetriever, save_retrieval_log
from ...schemas import AgentTrace, GenerateRequest, Profile, Resource
from .base import ResourceAgent


class VisualCardAgent(ResourceAgent):
    name = "VisualCardAgent"
    resource_type = "visual_card"
    content_format = "json"
    title_prefix = "可视化学习卡片"
    stage = "producer"
    boundary = "只产出卡片内容与动画提示，不渲染最终素材"
    depends_on = ["PlannerAgent", "KnowledgeAgent"]

    @staticmethod
    def _safe_pick(values: list, index: int, fallback: str) -> str:
        if not values:
            return fallback
        if index < len(values):
            return str(values[index])
        return str(values[index % len(values)])

    def content(self, state: WorkflowState) -> str:
        cards = []
        details = state.chapter.get("detailed_concepts", [])
        misconceptions = state.chapter.get("misconceptions", [])
        for idx, concept in enumerate(state.chapter["concepts"], start=1):
            detail = self._safe_pick(details, idx - 1, f"{state.chapter['title']} / {concept}")
            pitfall = self._safe_pick(misconceptions, idx - 1, f"学习 {concept} 时要避免只记术语、不结合案例。")
            cards.append(
                {
                    "id": f"card_{idx:02d}",
                    "title": concept,
                    "tagline": f"{state.chapter['title']} 核心要点",
                    "what": detail,
                    "pitfall": pitfall,
                    "check_question": f"如何判断场景中是否正确应用了“{concept}”？",
                    "animation_hint": "卡片翻转 + 重点词高亮",
                }
            )
        return json.dumps(
            {
                "cards": cards,
                "tool_handoff": {
                    "sync_to_tool": "预留给后续图像/动画生成工具",
                    "preferred_format": "png-sequence-or-lottie",
                },
            },
            ensure_ascii=False,
            indent=2,
        )

    def generate_content(self, state: WorkflowState) -> tuple[str, bool, str]:
        fallback = self.content(state)
        prompt = (
            "你是一个资深的计算机教授和教学视觉设计师，请基于给定的课程章节、核心概念和学生画像，"
            "生成一组可视化学习卡片内容。\n\n"
            "请输出格式严谨的 JSON，包含 cards 数组和 tool_handoff 字段。不要包裹在 ```json 代码块中，只输出纯 JSON 字符串。\n\n"
            "JSON 结构要求：\n"
            "- cards: 数组，每张卡片包含 id、title、tagline、what、pitfall、check_question、animation_hint。\n"
            "- tool_handoff: 对象，包含 sync_to_tool 和 preferred_format。\n\n"
            f"课程章节标题：{state.chapter['title']}\n"
            f"核心概念：{state.chapter['concepts']}\n"
            f"详细知识点：{state.chapter['detailed_concepts']}\n"
            f"常见误区：{state.chapter['misconceptions']}\n"
            f"代码实操任务：{state.chapter['code_labs']}\n"
            f"学生知识基础与偏好：{state.profile.knowledge_base}\n"
        )
        content, used_llm, reason = self.use_llm_or_fallback(prompt, fallback)
        if used_llm:
            try:
                parsed = parse_llm_json(content)
                if (
                    isinstance(parsed, dict)
                    and isinstance(parsed.get("cards"), list)
                    and "tool_handoff" in parsed
                ):
                    return json.dumps(parsed, ensure_ascii=False, indent=2), True, ""
                return fallback, False, "LLM returned visual card JSON without cards array or tool_handoff"
            except json.JSONDecodeError as exc:
                return fallback, False, f"LLM returned invalid visual card JSON: {exc}"
        return content, used_llm, reason

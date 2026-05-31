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


class MindMapAgent(ResourceAgent):
    name = "MindMapAgent"
    resource_type = "mind_map"
    content_format = "mermaid"
    title_prefix = "Mermaid 思维导图"
    stage = "producer"
    boundary = "只生成导图结构，不输出评估结论"
    depends_on = ["PlannerAgent", "KnowledgeAgent"]

    @staticmethod
    def _mindmap_label(value: object) -> str:
        text = str(value).strip()
        replacements = {
            "\n": " ",
            "\r": " ",
            "(": "（",
            ")": "）",
            "[": "【",
            "]": "】",
            "{": "｛",
            "}": "｝",
        }
        for source, target in replacements.items():
            text = text.replace(source, target)
        return re.sub(r"\s+", " ", text) or "未命名节点"

    @classmethod
    def _build_mindmap(cls, state: WorkflowState) -> str:
        lines = [
            "mindmap",
            f"  root(({cls._mindmap_label(state.chapter['title'])}))",
            "    学习目标",
            f"      {cls._mindmap_label(state.request.goal)}",
            "    核心概念",
        ]
        lines.extend(f"      {cls._mindmap_label(concept)}" for concept in state.chapter["concepts"])
        lines.append("    常见误区")
        lines.extend(f"      {cls._mindmap_label(item)}" for item in state.chapter["misconceptions"][:4])
        lines.append("    实践任务")
        lines.extend(f"      {cls._mindmap_label(item)}" for item in state.chapter["code_labs"][:3])
        return "\n".join(lines)

    @staticmethod
    def _strip_mermaid_fence(content: str) -> str:
        cleaned = content.strip()
        fence_match = re.search(r"```(?:mermaid)?\s*([\s\S]*?)\s*```", cleaned)
        return fence_match.group(1).strip() if fence_match else cleaned

    @classmethod
    def _is_valid_mindmap(cls, content: str) -> bool:
        cleaned = cls._strip_mermaid_fence(content)
        lines = [line.rstrip() for line in cleaned.splitlines() if line.strip()]
        if len(lines) < 3 or lines[0].strip() != "mindmap":
            return False
        if "-->" in cleaned:
            return False
        root_count = 0
        for index, line in enumerate(lines[1:], start=1):
            indent = len(line) - len(line.lstrip(" "))
            if indent % 2 != 0:
                return False
            if indent == 2:
                root_count += 1
                if index != 1 or not line.strip().startswith("root"):
                    return False
            elif indent < 2:
                return False
        return root_count == 1

    def content(self, state: WorkflowState) -> str:
        return self._build_mindmap(state)

    def generate_content(self, state: WorkflowState) -> tuple[str, bool, str]:
        fallback = self.content(state)
        prompt = (
            "你是一个资深的计算机教授，请基于给定的课程章节、核心概念和学生画像，"
            "生成一份结构清晰的 Mermaid 思维导图。\n\n"
            "只输出 Mermaid 语法的思维导图代码，不要包裹在 ```mermaid 这样的代码块中，不要输出任何其他解释性文字。\n\n"
            f"课程章节标题：{state.chapter['title']}\n"
            f"核心概念：{state.chapter['concepts']}\n"
            f"代码实操任务：{state.chapter['code_labs']}\n"
            f"学生知识基础与偏好：{state.profile.knowledge_base}\n"
        )
        content, used_llm, reason = self.use_llm_or_fallback(prompt, fallback)
        cleaned = self._strip_mermaid_fence(content)
        if self._is_valid_mindmap(cleaned):
            return cleaned, used_llm, reason
        return fallback, False, "LLM returned invalid Mermaid mindmap syntax"

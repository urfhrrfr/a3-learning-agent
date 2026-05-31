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


class ReadingAgent(ResourceAgent):
    name = "ReadingAgent"
    resource_type = "reading"
    title_prefix = "拓展阅读材料"
    stage = "producer"
    boundary = "只整理阅读与延伸，不参与最终仲裁"
    depends_on = ["PlannerAgent", "KnowledgeAgent"]

    def content(self, state: WorkflowState) -> str:
        real_cases = state.chapter["real_cases"]
        code_labs = state.chapter["code_labs"]
        return (
            "## 拓展阅读路线\n\n"
            "### 必读 1：教材对应章节\n"
            "- 阅读目标：圈出概念定义、公式出现的前提、评价方式。\n"
            "- 阅读产出：写下 3 个关键词和 1 个反例。\n\n"
            "### 必读 2：课程讲义案例\n"
            "- 阅读目标：观察案例里的输入、模型处理、输出解释。\n"
            "- 阅读产出：把案例改写成自己的专业或兴趣场景。\n\n"
            "### 选读 3：公开课程实验说明\n"
            "- 阅读目标：看清实验如何拆分数据、如何记录结果。\n"
            "- 阅读产出：列出你能复现的最小实验步骤。\n\n"
            "### 阅读检查问题\n"
            "1. 这个概念解决什么问题？\n"
            "2. 它在哪些条件下可能失效？\n"
            "3. 我能不能用一个 30 秒例子讲给同学听？\n\n"
            "### 真实案例延伸\n"
            f"{bullets(real_cases)}\n\n"
            "### 代码实验建议\n"
            f"{bullets(code_labs)}"
        )

    def generate_content(self, state: WorkflowState) -> tuple[str, bool, str]:
        fallback = self.content(state)
        prompt = (
            "你是一个资深的计算机教授和课程阅读设计专家。"
            "请基于给定的课程章节、核心概念、详细知识点和真实案例，生成一份拓展阅读指南和检查问题。\n\n"
            "输出要求：\n"
            "1. 使用中文 Markdown。\n"
            "2. 包含必读材料、选读材料、阅读目标、阅读产出和学习迁移建议。\n"
            "3. 必须包含一组阅读检查问题，帮助学生确认是否真正理解概念、边界条件和应用场景。\n"
            "4. 阅读建议要贴合学生已有知识基础和学习偏好。\n\n"
            f"课程章节标题：{state.chapter['title']}\n"
            f"核心概念：{state.chapter['concepts']}\n"
            f"详细知识点：{state.chapter['detailed_concepts']}\n"
            f"真实案例：{state.chapter['real_cases']}\n"
            f"代码实操任务：{state.chapter['code_labs']}\n"
            f"学生知识基础与偏好：{state.profile.knowledge_base}\n"
        )
        return self.use_llm_or_fallback(prompt, fallback)

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


class LectureAgent(ResourceAgent):
    name = "LectureAgent"
    resource_type = "lecture_doc"
    title_prefix = "课程讲解文档"
    stage = "producer"
    boundary = "只生成讲解文档，不修改题库或路径"
    depends_on = ["PlannerAgent", "KnowledgeAgent"]

    def _inline_cite(self, state: WorkflowState, index: int = 0) -> str:
        sources = self.evidence_sources(state)
        if not sources:
            return ""
        source_id = sources[min(index, len(sources) - 1)].get("id", "")
        return f" [来源: {source_id}]" if source_id else ""

    def content(self, state: WorkflowState) -> str:
        concepts = state.chapter["concepts"]
        detailed_concepts = state.chapter["detailed_concepts"]
        difficulties = state.chapter["difficulties"]
        misconceptions = state.chapter["misconceptions"]
        real_cases = state.chapter["real_cases"]
        pain_points = state.request.pain_points or state.profile.weak_points[:2]
        return (
            f"# {state.chapter['title']} 个性化讲解\n\n"
            "## 1. 本节课要解决的问题\n"
            f"你当前目标是：**{state.request.goal}**。本材料会先建立概念框架，再用一个校园学习场景把抽象术语落到输入、处理过程和输出。\n\n"
            "## 2. 学习目标\n"
            f"- 能用自己的话解释：{concepts[0]}、{concepts[1]}、{concepts[2]}、{concepts[3]}{self._inline_cite(state, 0)}\n"
            f"- 能判断一个案例中是否出现：{misconceptions[1]}{self._inline_cite(state, 1)}\n"
            f"- 能把薄弱点“{'、'.join(pain_points)}”转成可练习的小任务\n\n"
            "## 3. 核心概念速查\n"
            f"| 概念 | 一句话解释 | 学习时要抓住 |\n"
            f"| --- | --- | --- |\n"
            f"| {concepts[0]} | 模型看到并学习规律的样本或状态。{self._inline_cite(state, 0)} | 它是输入，不是最终结论。 |\n"
            f"| {concepts[1]} | 模型在新情况上继续有效的能力。{self._inline_cite(state, 1)} | 重点看新数据表现。 |\n"
            f"| {concepts[2]} | 衡量预测和真实目标差距的函数。{self._inline_cite(state, 2)} | 它决定优化方向。 |\n"
            f"| {concepts[3]} | 在已见数据上表现很好，但新数据变差。{self._inline_cite(state, 3)} | 需要测试集、正则化或更合理特征。 |\n\n"
            "## 4. 类比案例：校园课程推荐\n"
            "学校想给学生推荐课程。历史选课记录相当于训练数据，推荐算法相当于模型，学生是否真的喜欢推荐课程就是评价结果。"
            "如果系统只记住了上学期少数同学的选择，就可能在训练记录上表现很好，但遇到新同学时推荐失准，这就是过拟合的直观版本。\n\n"
            "## 5. 深入知识点说明\n"
            f"{bullets(detailed_concepts)}\n\n"
            "## 6. 更多真实案例\n"
            f"{bullets(real_cases)}\n\n"
            "## 7. 三步学习法\n"
            f"1. 先画输入输出：把“{state.chapter['title']}”中的数据、模型、评价写成三列。\n"
            f"2. 再找适用条件：重点检查 {difficulties[1]}，不要只背流程。\n"
            f"3. 最后做迁移练习：用自己的兴趣“{'、'.join(state.profile.interests[:2])}”重新造一个例子。\n\n"
            "## 8. 易错提醒\n"
            f"{bullets(misconceptions)}\n"
            "- 对线性代数薄弱的同学，先关注变量之间的方向关系，再看公式细节。\n\n"
            "## 9. 课后产出\n"
            "写一段 120 字小结：用一个生活例子解释“训练表现好”和“泛化表现好”的区别，并指出如何验证。"
        )

    def _build_grounded_prompt(self, state: WorkflowState) -> str:
        evidence_json = json.dumps(self.evidence_sources(state), ensure_ascii=False)
        return f"""SYSTEM:
你是高校课程讲解智能体。你必须遵守 Strict Grounding（严格锚定）规则：
1. 只能且必须基于 <EVIDENCE_CONTEXT> 中的 SOURCE 内容生成正文。
2. 严禁编造 <EVIDENCE_CONTEXT> 外的定义、事实、案例、实验步骤或结论。
3. 如果证据不足，请在正文中明确写“当前证据不足”，不要补充外部知识。
4. 正文中的核心概念、误区、案例和任务必须使用内联引用，格式为 [来源: source_id]。
5. 最终只返回 JSON 对象，不要 Markdown 代码块，不要额外解释。

USER:
课程章节：{state.chapter['title']}
学生当前目标：{state.request.goal}
学生画像摘要：
- 学习目标：{state.profile.learning_goal}
- 薄弱点：{'、'.join(state.profile.weak_points)}
- 常见错误模式：{'、'.join(state.profile.mistake_patterns)}
- 学习偏好：{state.profile.cognitive_style}；{'、'.join(state.profile.preferred_modalities)}

{self.evidence_xml_context(state)}

请生成中文 Markdown 讲解文档，并返回严格 JSON：
{{
  "content": "Markdown 正文。核心概念必须带 [来源: id] 内联引用。",
  "evidence_sources": {evidence_json}
}}
"""

    def _normalize_grounded_response(self, raw_content: str, state: WorkflowState) -> str | None:
        parsed = parse_llm_json(raw_content)
        if not isinstance(parsed, dict) or not isinstance(parsed.get("content"), str):
            return None
        allowed_ids = {str(source.get("id")) for source in self.evidence_sources(state)}
        returned_sources = parsed.get("evidence_sources", [])
        returned_ids = {
            str(source.get("id"))
            for source in returned_sources
            if isinstance(source, dict) and source.get("id")
        }
        if allowed_ids and not returned_ids.issubset(allowed_ids):
            return None
        content = parsed["content"].strip()
        if allowed_ids and "[来源:" not in content:
            return None
        return content

    def generate_content(self, state: WorkflowState) -> tuple[str, bool, str]:
        fallback = self.content(state)
        content, used_llm, reason = self.use_llm_or_fallback(self._build_grounded_prompt(state), fallback)
        if not used_llm:
            return content, used_llm, reason
        try:
            grounded_content = self._normalize_grounded_response(content, state)
        except json.JSONDecodeError as exc:
            return fallback, False, f"LLM returned invalid grounded lecture JSON: {exc}"
        if grounded_content:
            return grounded_content, True, ""
        return fallback, False, "LLM returned lecture content that violated strict grounding contract"

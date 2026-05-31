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


class QuizAgent(ResourceAgent):
    name = "QuizAgent"
    resource_type = "quiz"
    content_format = "json"
    title_prefix = "分层练习题"
    stage = "producer"
    boundary = "只生成题目及答案解析，不决定审核状态"
    depends_on = ["PlannerAgent", "KnowledgeAgent"]

    def _source_id(self, state: WorkflowState, index: int = 0) -> str:
        sources = self.evidence_sources(state)
        if not sources:
            return ""
        return str(sources[min(index, len(sources) - 1)].get("id", ""))

    def content(self, state: WorkflowState) -> str:
        questions = []
        for item in state.chapter["practice_questions"]:
            source_id = self._source_id(state, len(questions))
            citation = f" [来源: {source_id}]" if source_id else ""
            question = {
                "level": "基础" if item["type"] in {"choice", "true_false"} else "应用",
                "difficulty": item.get("difficulty", "基础" if item["type"] in {"choice", "true_false"} else "应用"),
                "type": item["type"],
                "question": f"{item['stem']}{citation}",
                "answer": item["standard_answer"],
                "explanation": f"{item['explanation']}{citation}",
                "assessment_point": item.get("assessment_point", ""),
                "rubric": item.get("rubric", []),
                "source_id": source_id,
            }
            if item["type"] == "choice":
                question["options"] = item.get(
                    "options",
                    [
                        "只看术语定义，不看任务目标",
                        "同时检查输入条件、处理逻辑与输出效果",
                        "优先选择训练误差最低方案",
                        "直接套用旧场景结论",
                    ],
                )
            if item["type"] == "true_false":
                question["options"] = item.get("options", ["正确", "错误"])
            questions.append(question)
        return json.dumps(questions, ensure_ascii=False, indent=2)

    def _build_grounded_prompt(self, state: WorkflowState) -> str:
        evidence_json = json.dumps(self.evidence_sources(state), ensure_ascii=False)
        return f"""SYSTEM:
你是高校课程练习题生成智能体。你必须遵守 Strict Grounding（严格锚定）规则：
1. 只能且必须基于 <EVIDENCE_CONTEXT> 中的 SOURCE 内容生成题目、答案和解析。
2. 严禁编造 <EVIDENCE_CONTEXT> 外的事实、概念边界、案例或实验结论。
3. 每道题必须绑定一个来自 <EVIDENCE_CONTEXT> 的 source_id。
4. question 或 explanation 至少一处必须包含内联引用 [来源: source_id]。
5. 最终只返回 JSON 对象，不要 Markdown 代码块，不要额外解释。

USER:
课程章节：{state.chapter['title']}
学生当前目标：{state.request.goal}
学生薄弱点：{'、'.join(state.profile.weak_points)}
题型要求：至少包含选择、判断、简答或场景题中的 3 类。

{self.evidence_xml_context(state)}

请返回严格 JSON：
{{
  "content": [
    {{
      "level": "基础/应用/提高",
      "difficulty": "基础/应用/提高/综合",
      "type": "choice/true_false/short_answer/scenario/code_reading",
      "question": "题干，必须带 [来源: id]",
      "answer": "标准答案",
      "explanation": "解析，必须基于证据并带 [来源: id]",
      "assessment_point": "考查点",
      "rubric": ["评分点"],
      "source_id": "证据 id",
      "options": ["选择题或判断题选项，可选"]
    }}
  ],
  "evidence_sources": {evidence_json}
}}
"""

    def _normalize_grounded_quiz(self, raw_content: str, state: WorkflowState) -> str | None:
        parsed = parse_llm_json(raw_content)
        items = parsed.get("content") if isinstance(parsed, dict) else parsed
        if not isinstance(items, list) or not items:
            return None
        allowed_ids = self.allowed_evidence_ids(state)
        normalized = []
        for item in items:
            if not isinstance(item, dict):
                return None
            source_id = str(item.get("source_id", ""))
            if allowed_ids and source_id not in allowed_ids:
                return None
            question = str(item.get("question", ""))
            explanation = str(item.get("explanation", ""))
            if allowed_ids and "[来源:" not in f"{question}\n{explanation}":
                return None
            normalized.append(item)
        return json.dumps(normalized, ensure_ascii=False, indent=2)

    def generate_content(self, state: WorkflowState) -> tuple[str, bool, str]:
        fallback = self.content(state)
        content, used_llm, reason = self.use_llm_or_fallback(self._build_grounded_prompt(state), fallback)
        if used_llm:
            try:
                grounded_quiz = self._normalize_grounded_quiz(content, state)
                if grounded_quiz:
                    return grounded_quiz, True, ""
                return fallback, False, "LLM returned quiz content that violated strict grounding contract"
            except json.JSONDecodeError as exc:
                return fallback, False, f"LLM returned invalid quiz JSON: {exc}"
        return content, used_llm, reason

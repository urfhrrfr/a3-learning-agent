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


class CodeCaseAgent(ResourceAgent):
    name = "CodeCaseAgent"
    resource_type = "code_case"
    content_format = "code"
    title_prefix = "Python 代码实操案例"
    stage = "producer"
    boundary = "只生成示例实验脚本，不执行真实沙箱评测"
    depends_on = ["PlannerAgent", "KnowledgeAgent"]

    def _source_id(self, state: WorkflowState, index: int = 0) -> str:
        sources = self.evidence_sources(state)
        if not sources:
            return ""
        return str(sources[min(index, len(sources) - 1)].get("id", ""))

    def content(self, state: WorkflowState) -> str:
        code_labs = state.chapter["code_labs"]
        source_id = self._source_id(state, 0)
        citation = f" [来源: {source_id}]" if source_id else ""
        return f'''"""
{state.chapter['title']}：多实验对比脚本（仅标准库）

学习目标：
1. 理解核心概念如何影响预测。{citation}
2. 对比理想样本、噪声样本与边界样本下的行为差异。{citation}
3. 把抽象术语转成可运行的验证证据。{citation}
"""

samples = [
    ([0.0, 0.0], "基础"),
    ([1.0, 1.0], "基础"),
    ([1.5, 1.2], "基础"),
    ([5.0, 5.0], "提高"),
    ([6.0, 5.0], "提高"),
    ([5.5, 6.0], "提高"),
]

test_cases = [
    ([1.2, 0.8], "基础"),
    ([5.2, 5.3], "提高"),
    ([3.0, 3.0], "边界样本"),
]


def distance(a, b):
    """计算两个二维点之间的欧氏距离。"""
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def predict(query):
    nearest = min(samples, key=lambda item: distance(item[0], query))
    return nearest[1], nearest


for features, label in test_cases:
    prediction, nearest = predict(features)
    print(f"样本 {{features}} | 真实标签: {{label}} | 预测: {{prediction}} | 最近训练样本: {{nearest}}")

noise_cases = [([2.0, 2.1], "可能偏移"), ([4.7, 4.8], "可能偏移")]
for features, label in noise_cases:
    prediction, nearest = predict(features)
    print(f"噪声样本 {{features}} | 标注: {{label}} | 预测: {{prediction}} | 参考: {{nearest}}")

print("\\n思考题：")
print("1. 为什么 [3.0, 3.0] 更难判断？")
print("2. 如果训练样本很少，模型为什么可能泛化不好？")
print("3. 你会增加哪些样本来让判断更可靠？")
print("\\n拓展实验：")
for item in {code_labs!r}:
    print("-", item, "{citation}")
'''

    def _build_grounded_prompt(self, state: WorkflowState) -> str:
        evidence_json = json.dumps(self.evidence_sources(state), ensure_ascii=False)
        return f"""SYSTEM:
你是高校课程代码实验生成智能体。你必须遵守 Strict Grounding（严格锚定）规则：
1. 只能且必须基于 <EVIDENCE_CONTEXT> 中的 SOURCE 内容生成代码案例。
2. 严禁编造 <EVIDENCE_CONTEXT> 外的算法事实、实验结论、数据假设或教学目标。
3. 代码注释或 docstring 中必须标注 [来源: source_id]。
4. 只输出 JSON 对象，不要 Markdown 代码块，不要额外解释。
5. 代码必须可直接保存为 Python 文件运行，优先仅使用标准库。

USER:
课程章节：{state.chapter['title']}
学生当前目标：{state.request.goal}
学生知识基础：{'、'.join(state.profile.knowledge_base)}
学生薄弱点：{'、'.join(state.profile.weak_points)}

{self.evidence_xml_context(state)}

请返回严格 JSON：
{{
  "content": "完整 Python 代码字符串。docstring 或关键注释必须带 [来源: id]。",
  "evidence_sources": {evidence_json}
}}
"""

    def _normalize_grounded_code(self, raw_content: str, state: WorkflowState) -> str | None:
        parsed = parse_llm_json(raw_content)
        if not isinstance(parsed, dict) or not isinstance(parsed.get("content"), str):
            return None
        content = parsed["content"].strip()
        if self.allowed_evidence_ids(state) and "[来源:" not in content:
            return None
        return content

    def generate_content(self, state: WorkflowState) -> tuple[str, bool, str]:
        fallback = self.content(state)
        content, used_llm, reason = self.use_llm_or_fallback(self._build_grounded_prompt(state), fallback)
        if not used_llm:
            return content, used_llm, reason
        try:
            grounded_code = self._normalize_grounded_code(content, state)
        except json.JSONDecodeError as exc:
            return fallback, False, f"LLM returned invalid code case JSON: {exc}"
        if grounded_code:
            return grounded_code, True, ""
        return fallback, False, "LLM returned code content that violated strict grounding contract"

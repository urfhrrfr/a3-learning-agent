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


class PlannerAgent(Agent):
    name = "PlannerAgent"
    role = "规划资源组合"
    stage = "planning"
    boundary = "只负责资源组合与任务拆分，不写具体内容"
    depends_on = ["KnowledgeAgent"]
    default_full_package_types = [
        "lecture_doc",
        "mind_map",
        "quiz",
        "reading",
        "animation_demo",
        "code_case",
        "html_ppt",
    ]

    resource_catalog = {
        "lecture_doc": {
            "label": "讲解文档",
            "difficulty": "入门",
            "estimated_minutes": 18,
            "base_priority": 0.78,
            "modalities": {"文字", "讲解", "例子"},
        },
        "mind_map": {
            "label": "思维导图",
            "difficulty": "入门",
            "estimated_minutes": 8,
            "base_priority": 0.62,
            "modalities": {"图解", "结构化"},
        },
        "quiz": {
            "label": "分层练习",
            "difficulty": "基础到提高",
            "estimated_minutes": 16,
            "base_priority": 0.82,
            "modalities": {"练习", "测验", "题目"},
        },
        "reading": {
            "label": "拓展阅读",
            "difficulty": "提高",
            "estimated_minutes": 20,
            "base_priority": 0.5,
            "modalities": {"阅读", "文字"},
        },
        "media_script": {
            "label": "视频/分镜脚本",
            "difficulty": "基础",
            "estimated_minutes": 12,
            "base_priority": 0.56,
            "modalities": {"短视频", "动画", "视听"},
        },
        "animation_demo": {
            "label": "教学动画",
            "difficulty": "基础",
            "estimated_minutes": 10,
            "base_priority": 0.58,
            "modalities": {"动画", "动态图", "图解"},
        },
        "html_ppt": {
            "label": "HTML PPT",
            "difficulty": "综合",
            "estimated_minutes": 18,
            "base_priority": 0.45,
            "modalities": {"PPT", "课件", "展示", "网页课件"},
        },
        "visual_card": {
            "label": "学习卡片",
            "difficulty": "入门",
            "estimated_minutes": 10,
            "base_priority": 0.6,
            "modalities": {"图解", "卡片", "记忆"},
        },
        "code_case": {
            "label": "代码案例",
            "difficulty": "应用",
            "estimated_minutes": 24,
            "base_priority": 0.66,
            "modalities": {"代码", "实操", "实验"},
        },
    }

    @staticmethod
    def _parse_time_budget_minutes(raw_budget: str) -> int | None:
        text = (raw_budget or "").strip()
        if not text:
            return None
        numbers = [int(value) for value in re.findall(r"\d+", text)]
        if not numbers:
            return None
        amount = numbers[0]
        if "小时" in text or "hour" in text.lower():
            return amount * 60
        return amount

    @staticmethod
    def _contains_any(text: str, keywords: set[str]) -> bool:
        lowered = text.lower()
        return any(keyword.lower() in lowered for keyword in keywords)

    def _score_resource(self, resource_type: str, state: WorkflowState) -> tuple[float, list[str]]:
        meta = self.resource_catalog[resource_type]
        profile = state.profile
        context = "；".join(
            [
                state.request.goal,
                "、".join(state.request.pain_points),
                profile.learning_goal,
                profile.cognitive_style,
                "、".join(profile.preferred_modalities),
                "、".join(profile.weak_points),
                "、".join(profile.mistake_patterns),
                "、".join(profile.knowledge_base),
            ]
        )
        score = float(meta["base_priority"])
        reasons: list[str] = []

        if meta["modalities"] & set(profile.preferred_modalities):
            score += 0.22
            reasons.append("匹配学习偏好")

        if "例子" in profile.cognitive_style and resource_type in {"lecture_doc", "media_script", "code_case"}:
            score += 0.12
            reasons.append("适合例子驱动型理解")

        if profile.mastery < 0.35 and resource_type in {"lecture_doc", "mind_map", "visual_card", "animation_demo", "quiz"}:
            score += 0.18
            reasons.append("当前掌握度偏低，优先补概念框架")
        elif profile.mastery >= 0.7 and resource_type in {"quiz", "code_case", "reading", "html_ppt"}:
            score += 0.16
            reasons.append("当前掌握度较高，增加迁移与输出任务")
        elif 0.35 <= profile.mastery < 0.7 and resource_type in {"lecture_doc", "quiz", "code_case", "mind_map"}:
            score += 0.12
            reasons.append("适合中等掌握度的讲练结合")

        if state.request.pain_points or profile.weak_points:
            if resource_type in {"quiz", "lecture_doc", "code_case"}:
                score += 0.16
                reasons.append("针对薄弱点安排讲解、练习或实操")

        if self._contains_any(context, {"混淆", "不懂", "概念", "定义"}):
            if resource_type in {"lecture_doc", "mind_map", "visual_card", "animation_demo"}:
                score += 0.14
                reasons.append("帮助澄清概念混淆")

        if self._contains_any(context, {"公式", "迁移", "实验", "项目", "代码", "python", "实操"}):
            if resource_type in {"code_case", "quiz", "lecture_doc"}:
                score += 0.14
                reasons.append("强化公式迁移或动手验证")

        if self._contains_any(context, {"考试", "练习", "测验", "巩固"}):
            if resource_type in {"quiz", "lecture_doc", "mind_map"}:
                score += 0.14
                reasons.append("服务练习巩固或考试复习")

        if self._contains_any(context, {"汇报", "展示", "课件", "ppt"}):
            if resource_type in {"html_ppt", "visual_card", "media_script"}:
                score += 0.18
                reasons.append("适合汇报展示产出")

        if self._contains_any(context, {"视频", "动画", "短视频", "图解"}):
            if resource_type in {"media_script", "animation_demo", "visual_card", "mind_map"}:
                score += 0.14
                reasons.append("匹配可视化或短视频偏好")

        if not reasons:
            reasons.append("作为基础资源组合的一部分")

        return round(min(score, 1.0), 2), reasons

    def _target_resource_count(self, state: WorkflowState, allowed_count: int) -> int:
        if state.request.resource_types:
            return allowed_count
        minutes = self._parse_time_budget_minutes(state.profile.time_budget)
        if minutes is None:
            return min(7, allowed_count)
        if minutes <= 20:
            return min(4, allowed_count)
        if minutes <= 45:
            return min(6, allowed_count)
        if minutes <= 75:
            return min(7, allowed_count)
        return allowed_count

    def run(self, state: WorkflowState) -> dict:
        default_types = set(self.default_full_package_types)
        allowed_types = [
            resource_type
            for resource_type in self.resource_catalog
            if (
                resource_type in state.request.resource_types
                if state.request.resource_types
                else resource_type in default_types
            )
        ]
        scored = []
        for resource_type in allowed_types:
            score, reasons = self._score_resource(resource_type, state)
            scored.append(
                {
                    "type": resource_type,
                    "label": self.resource_catalog[resource_type]["label"],
                    "priority": score,
                    "difficulty": self.resource_catalog[resource_type]["difficulty"],
                    "estimated_minutes": self.resource_catalog[resource_type]["estimated_minutes"],
                    "reason": "；".join(reasons[:3]),
                }
            )

        scored.sort(key=lambda item: (-item["priority"], item["estimated_minutes"], item["type"]))
        selected = scored[: self._target_resource_count(state, len(scored))]
        state.plan = [item["type"] for item in selected]
        state.plan_details = selected
        state.learning_context["preferred_resources"] = selected

        total_minutes = sum(item["estimated_minutes"] for item in selected)
        labels = "、".join(item["label"] for item in selected)
        return {
            "summary": f"规划 {len(selected)} 类资源：{labels}；预计学习 {total_minutes} 分钟",
            "confidence": round(sum(item["priority"] for item in selected) / max(len(selected), 1), 2),
            "arbitration_note": "按学生偏好、掌握度、薄弱点、目标关键词与时间预算综合排序；显式 resource_types 会作为硬约束。",
            "review_conclusion": "规划明细：" + " | ".join(
                f"{item['label']} priority={item['priority']:.2f} reason={item['reason']}"
                for item in selected
            ),
        }

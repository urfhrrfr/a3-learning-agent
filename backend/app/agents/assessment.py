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


class AssessmentAgent(Agent):
    name = "AssessmentAgent"
    role = "评估学习效果并调整路径"
    stage = "assessment"
    boundary = "负责评估学习效果、生成报告，不直接生成资源"

    def __init__(self, llm: BaseLLMProvider | None = None):
        super().__init__(llm)
        self.confidence_threshold = 0.6

    def _extract_json_from_response(self, text: str) -> dict | None:
        """从 LLM 响应中提取 JSON"""
        text = text.strip()
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = text
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None

    def _calculate_basic_stats(self, quiz_answers: list[dict]) -> dict:
        """计算基础统计数据"""
        if not quiz_answers:
            return {
                "total": 0,
                "correct": 0,
                "accuracy": 0.0,
                "by_type": {}
            }

        total = len(quiz_answers)
        correct = sum(1 for ans in quiz_answers if ans.get("is_correct", False))
        accuracy = correct / total if total > 0 else 0.0

        by_type = {}
        for ans in quiz_answers:
            q_type = ans.get("type", "unknown")
            if q_type not in by_type:
                by_type[q_type] = {"total": 0, "correct": 0}
            by_type[q_type]["total"] += 1
            if ans.get("is_correct", False):
                by_type[q_type]["correct"] += 1

        return {
            "total": total,
            "correct": correct,
            "accuracy": accuracy,
            "by_type": by_type
        }

    def _infer_cognitive_level(self, quiz_answers: list[dict], stats: dict) -> dict:
        """推断认知水平"""
        type_map = {
            "choice": "理解",
            "true_false": "记忆",
            "short_answer": "应用",
            "code_reading": "分析",
            "scenario": "评价"
        }

        cognitive_distribution = {}
        for ans in quiz_answers:
            q_type = ans.get("type", "unknown")
            level = type_map.get(q_type, "理解")
            cognitive_distribution[level] = cognitive_distribution.get(level, 0) + 1

        dominant_level = max(cognitive_distribution, key=cognitive_distribution.get) if cognitive_distribution else "理解"

        level_descriptions = {
            "记忆": "学生能够识别和回忆基本概念",
            "理解": "学生能够解释和举例说明概念",
            "应用": "学生能够在新情境中使用所学知识",
            "分析": "学生能够分解问题并识别关系",
            "评价": "学生能够基于标准进行判断",
            "创造": "学生能够综合知识产生新想法"
        }

        return {
            "level": dominant_level,
            "description": level_descriptions.get(dominant_level, "学生能够理解基本概念"),
            "distribution": cognitive_distribution
        }

    def _identify_weak_points(self, quiz_answers: list[dict], profile: dict) -> list[dict]:
        """识别薄弱点"""
        weak_points = []

        wrong_answers = [ans for ans in quiz_answers if not ans.get("is_correct", False)]

        for ans in wrong_answers:
            question = ans.get("question", "")
            explanation = ans.get("explanation", "")

            topics = []
            if "梯度" in question or "梯度下降" in question:
                topics.append("梯度下降")
            if "评估" in question or "指标" in question:
                topics.append("模型评估指标")
            if "过拟合" in question:
                topics.append("过拟合与欠拟合")
            if "泛化" in question:
                topics.append("泛化能力")
            if "损失函数" in question:
                topics.append("损失函数")
            if "正则化" in question:
                topics.append("正则化")

            for topic in topics:
                existing = next((wp for wp in weak_points if wp["topic"] == topic), None)
                if existing:
                    existing["count"] = existing.get("count", 1) + 1
                else:
                    weak_points.append({
                        "topic": topic,
                        "severity": "高" if len(topics) > 1 else "中",
                        "evidence": explanation[:100] if explanation else "答题错误",
                        "count": 1
                    })

        profile_weak = profile.get("weak_points", [])
        for weak in profile_weak:
            if not any(wp["topic"] == weak for wp in weak_points):
                weak_points.append({
                    "topic": weak,
                    "severity": "中",
                    "evidence": "从画像中识别",
                    "count": 0
                })

        weak_points.sort(key=lambda x: x.get("count", 0), reverse=True)
        return weak_points[:5]

    def _identify_strengths(self, quiz_answers: list[dict], stats: dict) -> list[str]:
        """识别优势"""
        strengths = []

        correct_answers = [ans for ans in quiz_answers if ans.get("is_correct", False)]

        for ans in correct_answers:
            question = ans.get("question", "")
            if "过拟合" in question:
                strengths.append("能正确识别过拟合现象")
            if "泛化" in question:
                strengths.append("理解训练集与测试集的分工")
            if "损失函数" in question:
                strengths.append("理解损失函数的作用")
            if "概念" in question and ("选择" in question or "判断" in question):
                strengths.append("掌握核心概念的定义")

        if stats.get("accuracy", 0) >= 0.85:
            strengths.append("整体正确率高，学习效果良好")

        strengths = list(dict.fromkeys(strengths))
        return strengths[:3]

    def _calculate_mastery_delta(self, current_mastery: float, accuracy: float) -> float:
        """计算掌握度变化"""
        if accuracy >= 0.9:
            return 0.15
        elif accuracy >= 0.8:
            return 0.10
        elif accuracy >= 0.7:
            return 0.05
        elif accuracy >= 0.6:
            return 0.02
        else:
            return -0.05

    def _fallback_assessment(
        self,
        quiz_answers: list[dict],
        profile: dict,
        stats: dict
    ) -> dict:
        """后备评估方法（当LLM不可用时）"""
        cognitive = self._infer_cognitive_level(quiz_answers, stats)
        weak_points = self._identify_weak_points(quiz_answers, profile)
        strengths = self._identify_strengths(quiz_answers, stats)
        mastery_delta = self._calculate_mastery_delta(profile.get("mastery", 0.4), stats.get("accuracy", 0))

        recommendations = []
        if mastery_delta < 0:
            recommendations.append("建议重新学习相关概念，加强基础理解")
        elif mastery_delta < 0.05:
            recommendations.append("建议多做练习题，巩固已学知识")
        else:
            recommendations.append("当前学习效果良好，可以继续深入学习")

        if weak_points:
            recommendations.append(f"重点加强：{', '.join(wp['topic'] for wp in weak_points[:2])}")

        return {
            "assessment": {
                "knowledge_mastery": {
                    "score": round(stats.get("accuracy", 0.5), 2),
                    "level": "优秀" if stats.get("accuracy", 0) >= 0.9 else "良好" if stats.get("accuracy", 0) >= 0.7 else "需加强",
                    "details": f"共{stats['total']}题，正确{stats['correct']}题"
                },
                "cognitive_level": cognitive,
                "learning_efficiency": {
                    "score": round(stats.get("accuracy", 0.5) * 0.8 + 0.2, 2),
                    "description": "学习投入产出比正常"
                },
                "weak_points": weak_points,
                "strengths": strengths
            },
            "mastery_delta": round(mastery_delta, 2),
            "next_learning_objectives": recommendations,
            "confidence": 0.6,
            "reasoning": "基于规则的后备评估（LLM不可用）"
        }

    def assess(
        self,
        quiz_answers: list[dict],
        profile: Profile,
        resource_usage: list[dict] | None = None,
        learning_history: list[dict] | None = None
    ) -> dict:
        """执行学习效果评估"""
        profile_dict = profile.model_dump()
        stats = self._calculate_basic_stats(quiz_answers)

        if len(quiz_answers) == 0:
            return {
                "assessment": {
                    "knowledge_mastery": {"score": profile.mastery, "level": "待评估", "details": "暂无答题数据"},
                    "cognitive_level": {"level": "待确定", "description": "暂无认知数据"},
                    "learning_efficiency": {"score": 0.5, "description": "暂无学习数据"},
                    "weak_points": [],
                    "strengths": []
                },
                "mastery_delta": 0.0,
                "next_learning_objectives": ["完成练习题以获取评估数据"],
                "confidence": 0.3,
                "reasoning": "无答题数据，无法进行评估"
            }

        try:
            prompt = build_assessment_prompt(
                profile_dict,
                quiz_answers,
                resource_usage,
                learning_history
            )
            response = self.llm.complete(prompt)
            result = self._extract_json_from_response(response)

            if result and "assessment" in result:
                confidence = result.get("confidence", 0.5)
                if confidence >= self.confidence_threshold:
                    return result
        except (LLMProviderError, Exception):
            pass

        return self._fallback_assessment(quiz_answers, profile_dict, stats)

    def run(self, state: WorkflowState) -> dict:
        """执行评估（用于评估流程）"""
        quiz_answers = state.request.pain_points
        result = self.assess(quiz_answers, state.profile)
        return {
            "summary": f"评估完成：掌握度 {result.get('mastery_delta', 0):+.2f}",
            "confidence": result.get("confidence", 0.5),
            "assessment_result": result
        }

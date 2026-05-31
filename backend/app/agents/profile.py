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


class ProfileAgent(Agent):
    name = "ProfileAgent"
    role = "从对话抽取画像"
    stage = "profile"

    PREREQUISITE_WEAK_POINTS = {"概率论", "线性代数", "高等数学", "Python"}
    PREREQUISITE_MENTION_TERMS = {
        "概率论": ["概率论", "概率", "贝叶斯", "条件概率", "统计"],
        "线性代数": ["线性代数", "线代", "矩阵", "向量"],
        "高等数学": ["高等数学", "高数", "微积分", "导数"],
        "Python": ["python", "编程基础", "代码基础"],
    }
    boundary = "负责从自然语言对话中抽取学习特征，不直接生成资源"

    def __init__(
        self,
        llm: BaseLLMProvider | None = None,
        normalizer: ProfileNormalizer | None = None,
        validator: ProfileValidator | None = None,
    ):
        super().__init__(llm)
        self.confidence_threshold = 0.6
        self.last_fusion_meta: dict = {}
        self.normalizer = normalizer or ProfileNormalizer()
        self.validator = validator or ProfileValidator(self.normalizer)

    def _extract_json_from_response(self, text: str) -> dict | None:
        """从 LLM 响应中提取 JSON"""
        try:
            return parse_llm_json(text)
        except json.JSONDecodeError:
            return None

    def _fallback_extract(self, message: str) -> dict:
        """当 LLM 不可用时的后备提取方法（基于轻量语义规则）"""
        extracted = {
            "knowledge_base": [],
            "learning_goal": "",
            "cognitive_style": "",
            "preferred_modalities": [],
            "weak_points": [],
            "mistake_patterns": [],
            "time_budget": "",
            "interests": []
        }

        message_lower = message.lower()
        weak_markers = ["差", "弱", "不好", "不太好", "跟不上", "搞不懂", "不懂", "混淆", "容易错", "不会"]

        if "数学" in message_lower or "线代" in message_lower or "线性代数" in message_lower:
            if any(marker in message_lower for marker in weak_markers):
                extracted["knowledge_base"].append("线性代数薄弱")
                extracted["weak_points"].append("线性代数")
            else:
                extracted["knowledge_base"].append("数学基础")
        if "python" in message_lower:
            if any(marker in message_lower for marker in ["python差", "python弱", "python不好", "python不太好"]):
                extracted["knowledge_base"].append("Python薄弱")
            else:
                extracted["knowledge_base"].append("Python基础")

        if "考研" in message_lower:
            extracted["learning_goal"] = "准备考研"
        elif "考试" in message_lower:
            extracted["learning_goal"] = "通过期末考试"
        elif "项目" in message_lower:
            extracted["learning_goal"] = "完成课程项目"

        if "例子" in message_lower or "案例" in message_lower:
            extracted["cognitive_style"] = "例子驱动"
        elif "结构" in message_lower or "框架" in message_lower:
            extracted["cognitive_style"] = "结构化推理"
        elif "实践" in message_lower or "动手" in message_lower:
            extracted["cognitive_style"] = "先实践后理论"

        if "图解" in message_lower or "图" in message_lower:
            extracted["preferred_modalities"].append("图解")
        if "代码" in message_lower or "python" in message_lower:
            extracted["preferred_modalities"].append("代码案例")
        if "视频" in message_lower or "动画" in message_lower:
            extracted["preferred_modalities"].append("短视频")
        if "阅读" in message_lower or "书" in message_lower:
            extracted["preferred_modalities"].append("阅读材料")

        if "梯度" in message_lower:
            extracted["weak_points"].append("梯度下降")
        if "评估" in message_lower:
            extracted["weak_points"].append("模型评估指标")
        if "反向" in message_lower:
            extracted["weak_points"].append("反向传播")
        if "混淆" in message_lower:
            extracted["mistake_patterns"].append("概念混淆")
        if "迁移" in message_lower or "不会用" in message_lower:
            extracted["mistake_patterns"].append("知识迁移困难")

        extracted["weak_points"].extend(self._explicit_course_weak_points(message))

        time_match = re.search(r'每天[^\d]*(\d+)', message_lower)
        if time_match:
            extracted["time_budget"] = f"每天{time_match.group(1)}分钟"
        else:
            weekly_match = re.search(r'每周[^\d]*(\d+)', message_lower)
            if weekly_match:
                extracted["time_budget"] = f"每周{weekly_match.group(1)}小时"

        if "教育" in message_lower:
            extracted["interests"].append("智能教育")
        if "机器学习" in message_lower:
            extracted["interests"].append("机器学习应用")
        if "视觉" in message_lower:
            extracted["interests"].append("计算机视觉")
        if "nlp" in message_lower or "自然语言" in message_lower:
            extracted["interests"].append("自然语言处理")

        return extracted

    def _explicit_course_weak_points(self, message: str) -> list[str]:
        message_lower = message.lower()
        topics: list[str] = []
        topic_rules = [
            ("A*搜索", ["a*搜索", "a * 搜索", "a星搜索", "a 星搜索", "a*", "astar"]),
            ("过拟合", ["过拟合", "overfitting"]),
            ("Transformer自注意力", ["transformer 自注意力", "transformer自注意力", "自注意力", "self-attention"]),
            ("RAG", ["rag", "检索增强生成"]),
            ("Top-K检索", ["top-k", "topk", "top k"]),
            ("重排序", ["重排序", "rerank", "reranking"]),
            ("Q-learning", ["q-learning", "qlearning", "q learning"]),
        ]
        for canonical, aliases in topic_rules:
            if any(alias in message_lower for alias in aliases):
                topics.append(canonical)
        return self.normalizer.normalize_tags(topics)

    def _message_mentions_prerequisite(self, message: str, topic: str) -> bool:
        message_lower = message.lower()
        return any(term.lower() in message_lower for term in self.PREREQUISITE_MENTION_TERMS.get(topic, [topic]))

    def _should_replace_current_weak_points(self, message: str, explicit_points: list[str]) -> bool:
        if not explicit_points:
            return False
        replace_markers = ["我现在对", "我对", "比较困惑", "困惑", "不懂", "搞不懂", "当前", "现在"]
        return any(marker in message for marker in replace_markers)

    def _align_profile_to_latest_message(self, profile: Profile, latest_message: str) -> Profile:
        if not latest_message:
            return profile

        explicit_points = self._explicit_course_weak_points(latest_message)
        if not explicit_points:
            return profile

        data = profile.model_dump()
        current_weak_points = self.normalizer.normalize_tags(data.get("weak_points", []))
        explicit_set = set(explicit_points)
        replace_current = self._should_replace_current_weak_points(latest_message, explicit_points)

        cleaned_weak_points: list[str] = []
        if replace_current:
            cleaned_weak_points.extend(explicit_points)
            for point in current_weak_points:
                if point in explicit_set:
                    continue
                if point in self.PREREQUISITE_WEAK_POINTS and not self._message_mentions_prerequisite(latest_message, point):
                    continue
                cleaned_weak_points.append(point)
        else:
            cleaned_weak_points = self.normalizer.normalize_tags([*explicit_points, *current_weak_points])

        data["weak_points"] = self.normalizer.normalize_tags(cleaned_weak_points)

        if replace_current:
            data["knowledge_base"] = [
                item
                for item in self.normalizer.normalize_tags(data.get("knowledge_base", []))
                if item not in self.PREREQUISITE_WEAK_POINTS or self._message_mentions_prerequisite(latest_message, item)
            ]
            goal = str(data.get("learning_goal") or "")
            for topic in self.PREREQUISITE_WEAK_POINTS:
                if self._message_mentions_prerequisite(latest_message, topic):
                    continue
                goal = re.sub(rf"[，,；;、]?\s*(并)?(优先)?(补习|补|学习|巩固)?{re.escape(topic)}(等)?(基础)?", "", goal)
            data["learning_goal"] = goal.strip("，,；;、 ") or data.get("learning_goal", "")
        return Profile(**data)

    def turn_snapshot_from_extraction(
        self,
        extracted_features: dict | None,
        latest_message: str = "",
        base_profile: Profile | None = None,
    ) -> Profile:
        """Build a per-turn profile snapshot that does not inherit historical weak points."""
        extracted_features = extracted_features or {}
        base = base_profile.model_dump() if base_profile else {}
        data = Profile().model_dump()
        data["id"] = base.get("id", data["id"])
        data["version"] = base.get("version", data["version"])
        data["updated_at"] = base.get("updated_at", data["updated_at"])

        for field in ["major", "education_level", "course", "current_chapter"]:
            data[field] = extracted_features.get(field) or base.get(field) or data[field]
        for field in ["learning_goal", "cognitive_style", "time_budget"]:
            data[field] = extracted_features.get(field) or ""
        for field in ["knowledge_base", "preferred_modalities", "weak_points", "mistake_patterns", "interests"]:
            data[field] = self.normalizer.normalize_tags(extracted_features.get(field, []))

        explicit_points = self._explicit_course_weak_points(latest_message)
        if explicit_points:
            data["weak_points"] = self.normalizer.normalize_tags([*explicit_points, *data["weak_points"]])
        return self._align_profile_to_latest_message(Profile(**data), latest_message)

    def extract(self, message: str, current_profile: Profile | None = None) -> dict:
        """从对话中抽取特征"""
        current_profile_dict = None
        if current_profile:
            current_profile_dict = current_profile.model_dump()

        try:
            prompt = build_profile_extraction_prompt(message, current_profile_dict)
            response = self.llm.complete(prompt)
            result = self._extract_json_from_response(response)

            if result and "extracted" in result:
                confidence = result.get("confidence", 0.5)
                if confidence >= self.confidence_threshold:
                    return {
                        "extracted": result["extracted"],
                        "confidence": confidence,
                        "reasoning": result.get("reasoning", "LLM抽取"),
                        "source": "llm"
                    }
        except LLMProviderError:
            pass

        fallback = self._fallback_extract(message)
        return {
            "extracted": fallback,
            "confidence": 0.5,
            "reasoning": "轻量语义规则（LLM不可用或置信度低）",
            "source": "fallback"
        }

    def _fuse_list(self, current: list[str], new: list[str], field: str) -> list[str]:
        """融合列表型字段，去重"""
        return self.normalizer.normalize_tags(new + current)

    def _fuse_string(self, current: str, new: str, is_conflict: bool = False) -> str:
        """融合字符串型字段，新值优先"""
        if new and is_conflict:
            return new
        if new:
            return new
        return current

    def _detect_conflict(self, current: str | list, new: str | list, field: str) -> tuple[bool, str]:
        """检测冲突"""
        if isinstance(current, str) and isinstance(new, str):
            if current and new and current != new:
                return True, f"{field}: '{current}' -> '{new}'"
        return False, ""

    def _diff_profile_fields(self, before: Profile, after: Profile) -> list[str]:
        fields = [
            "knowledge_base",
            "learning_goal",
            "cognitive_style",
            "preferred_modalities",
            "weak_points",
            "mistake_patterns",
            "time_budget",
            "interests",
            "mastery",
        ]
        before_dict = before.model_dump()
        after_dict = after.model_dump()
        return [field for field in fields if before_dict.get(field) != after_dict.get(field)]

    def _semantic_fuse_with_llm(self, current_profile: Profile, latest_message: str) -> tuple[Profile, list[str], str] | None:
        self.last_fusion_meta = {}
        if not latest_message.strip() or self.llm.name == "mock":
            return None

        prompt = build_profile_semantic_fusion_prompt(
            current_profile.model_dump(),
            latest_message,
        )
        response = self.llm.complete(prompt)
        data = self._extract_json_from_response(response)
        if not isinstance(data, dict):
            return None

        raw_result = data
        profile_data = data
        if "profile" in data and isinstance(data["profile"], dict):
            profile_data = data["profile"]
        elif "fused" in data and isinstance(data["fused"], dict):
            profile_data = data["fused"]

        merged = current_profile.model_dump()
        merged.update(profile_data)
        merged["id"] = current_profile.id
        merged["version"] = current_profile.version
        merged["updated_at"] = current_profile.updated_at

        fused_profile = self._align_profile_to_latest_message(Profile(**merged), latest_message)
        changed_fields = raw_result.get("changed_fields") or self._diff_profile_fields(current_profile, fused_profile)
        conflicts = raw_result.get("conflicts") or []
        reasoning = raw_result.get("merge_reasoning") or "LLM语义融合完成：已根据最新对话进行近义词合并、隐含语义理解和冲突处理"
        confidence = raw_result.get("confidence", 0.75)
        validation = self.validator.evaluate_fusion(
            current_profile.model_dump(),
            fused_profile.model_dump(),
            latest_message,
        )
        self.last_fusion_meta = {
            "source": "llm",
            "changed_fields": changed_fields,
            "conflicts": conflicts,
            "merge_reasoning": reasoning,
            "confidence": confidence,
            "validation": validation,
        }
        conflict_summaries = [
            f"{item.get('field', 'unknown')}: {item.get('before', '')} -> {item.get('after', '')}；{item.get('reason', '')}"
            if isinstance(item, dict)
            else str(item)
            for item in conflicts
        ]
        return fused_profile, conflict_summaries, reasoning

    def fuse(
        self,
        current_profile: Profile,
        extracted: dict | None = None,
        latest_message: str = "",
    ) -> tuple[Profile, list[str], str]:
        """融合画像；优先使用 LLM 基于最新自然语言对话做语义融合。"""
        self.last_fusion_meta = {}
        if latest_message:
            try:
                semantic_result = self._semantic_fuse_with_llm(current_profile, latest_message)
                if semantic_result is not None:
                    return semantic_result
            except (LLMProviderError, ValueError, TypeError, json.JSONDecodeError):
                pass

        current_dict = current_profile.model_dump()
        extracted_features = (extracted or {}).get("extracted", {})
        conflicts = []

        for field in ["knowledge_base", "preferred_modalities", "weak_points", "mistake_patterns", "interests"]:
            current_dict[field] = self._fuse_list(
                current_dict.get(field, []),
                extracted_features.get(field, []),
                field,
            )

        for field in ["learning_goal", "cognitive_style", "time_budget"]:
            new_val = extracted_features.get(field, "")
            is_conflict, conflict_msg = self._detect_conflict(current_dict.get(field, ""), new_val, field)
            if is_conflict:
                conflicts.append(conflict_msg)
            current_dict[field] = self._fuse_string(current_dict.get(field, ""), new_val, is_conflict)

        fused_profile = self._align_profile_to_latest_message(Profile(**current_dict), latest_message)
        reasoning = "画像融合完成"
        if conflicts:
            reasoning += f"，检测到{len(conflicts)}处冲突并已按最新信息更新"

        self.last_fusion_meta = {
            "source": "fallback",
            "changed_fields": self._diff_profile_fields(current_profile, fused_profile),
            "conflicts": conflicts,
            "merge_reasoning": reasoning,
            "confidence": 0.5,
            "validation": self.validator.evaluate_fusion(
                current_profile.model_dump(),
                fused_profile.model_dump(),
                latest_message,
            ),
        }
        return fused_profile, conflicts, reasoning

    def run(self, state: WorkflowState) -> dict:
        """执行画像抽取（用于资源生成流程）"""
        return {
            "summary": "ProfileAgent 准备就绪",
            "confidence": 0.9
        }

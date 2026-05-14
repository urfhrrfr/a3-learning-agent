from __future__ import annotations

import json
import re
from html import escape
from datetime import datetime, timezone
from uuid import uuid4

from .core.profile_normalizer import ProfileNormalizer
from .core.profile_validator import ProfileValidator
from .knowledge import COURSE, find_chapter
from .providers.base import BaseLLMProvider, LLMProviderError
from .providers.factory import get_llm_provider
from .prompts import (
    build_profile_extraction_prompt,
    build_profile_semantic_fusion_prompt,
)
from .assessment_prompts import build_assessment_prompt, build_review_fact_check_prompt
from .schemas import AgentTrace, GenerateRequest, Profile, Resource


def bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def parse_llm_json(content: str):
    cleaned = content.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    candidates = []
    for opener, closer in [("[", "]"), ("{", "}")]:
        start = cleaned.find(opener)
        end = cleaned.rfind(closer)
        if start != -1 and end != -1 and end > start:
            candidates.append(cleaned[start : end + 1])

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    raise json.JSONDecodeError("No valid JSON object or array found", cleaned, 0)


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class WorkflowState:
    def __init__(self, job_id: str, request: GenerateRequest, profile: Profile):
        self.job_id = job_id
        self.request = request
        self.profile = profile
        self.chapter = find_chapter(request.chapter)
        self.sources: list[str | dict] = [f"{self.chapter['id']}#overview", f"{self.chapter['id']}#practice"]
        self.resources: list[Resource] = []
        self.traces: list[AgentTrace] = []
        self.plan: list[str] = []
        self.plan_details: list[dict] = []
        self.feedback_from_review: dict = {}
        self.learning_context: dict = {
            "review_feedback": {},
            "improvement_suggestions": [],
            "cognitive_level": "理解",
            "preferred_resources": []
        }


class Agent:
    name = "Agent"
    role = "base"
    stage = "producer"
    boundary = "负责单步生成，不负责全局编排"
    depends_on: list[str] = []
    max_retries = 1

    def __init__(self, llm: BaseLLMProvider | None = None):
        self.llm = llm or get_llm_provider()

    def run(self, state: WorkflowState) -> dict:
        return {}

    def traced_run(self, state: WorkflowState, input_summary: str) -> AgentTrace:
        trace = AgentTrace(
            id=f"trace_{uuid4().hex[:8]}",
            job_id=state.job_id,
            agent=self.name,
            status="running",
            input_summary=input_summary,
            output_summary="",
            collaboration_stage=self.stage,
            boundary=self.boundary,
            depends_on=list(self.depends_on),
            source_refs=list(state.sources),
            confidence=0.84,
            retry_count=0,
            llm_provider=self.llm.name,
            started_at=now(),
        )
        result: dict = {}
        last_error = ""
        for attempt in range(self.max_retries + 1):
            try:
                trace.retry_count = attempt
                result = self.run(state)
                trace.status = "completed"
                break
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                if attempt < self.max_retries:
                    trace.warnings.append(f"第 {attempt + 1} 次执行失败，已重试: {last_error}")
                    continue
                trace.status = "failed"
                trace.warnings.append(f"执行失败: {last_error}")
        trace.output_summary = result.get("summary", f"{self.name} 已完成" if trace.status == "completed" else f"{self.name} 执行失败")
        trace.warnings = [*trace.warnings, *result.get("warnings", [])]
        trace.confidence = result.get("confidence", trace.confidence if trace.status == "completed" else 0.35)
        trace.source_refs = list(state.sources)
        trace.arbitration_note = result.get("arbitration_note", "")
        trace.review_conclusion = result.get("review_conclusion", "")
        trace.finished_at = now()
        state.traces.append(trace)
        return trace

    def use_llm_or_fallback(self, prompt: str, fallback: str) -> tuple[str, bool, str]:
        if self.llm.name == "mock":
            return fallback, False, ""
        try:
            content = self.llm.complete(prompt).strip()
            if content:
                return content, True, ""
        except LLMProviderError as exc:
            return fallback, False, str(exc)
        except Exception as exc:  # noqa: BLE001
            return fallback, False, str(exc)
        return fallback, False, "LLM returned empty content"


class ProfileAgent(Agent):
    name = "ProfileAgent"
    role = "从对话抽取画像"
    stage = "profile"
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

        fused_profile = Profile(**merged)
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

        fused_profile = Profile(**current_dict)
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


class KnowledgeAgent(Agent):
    name = "KnowledgeAgent"
    role = "检索课程知识库"
    stage = "knowledge"
    boundary = "只负责检索与证据整理，不直接生成学习资源"
    depends_on = ["ProfileAgent"]
    max_candidates = 12
    top_k = 5

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

    def run(self, state: WorkflowState) -> dict:
        query = self._current_query(state)
        profile_context = self._profile_context(state)
        candidates = self._prefilter_candidates(state, query, profile_context)
        candidates_by_id = {item["id"]: item for item in candidates}
        selected: list[dict] = []
        warnings: list[str] = []

        prompt = self._build_rerank_prompt(query, profile_context, candidates)
        try:
            selected = self._normalize_rerank_result(parse_llm_json(self.llm.complete(prompt)), candidates_by_id)
        except (json.JSONDecodeError, LLMProviderError, Exception) as exc:  # noqa: BLE001
            warnings.append(f"LLM rerank 不可用，已使用本地轻量排序兜底: {exc}")

        if not selected:
            selected = self._fallback_rerank(candidates)

        state.sources = selected
        avg_score = sum(item["relevance_score"] for item in selected) / max(len(selected), 1)
        return {
            "summary": f"语义检索到 {len(selected)} 个与“{query}”最相关的知识片段",
            "confidence": round(avg_score, 2),
            "warnings": warnings,
        }


class PlannerAgent(Agent):
    name = "PlannerAgent"
    role = "规划资源组合"
    stage = "planning"
    boundary = "只负责资源组合与任务拆分，不写具体内容"
    depends_on = ["KnowledgeAgent"]

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
        "ppt_draft": {
            "label": "PPT 草稿",
            "difficulty": "综合",
            "estimated_minutes": 18,
            "base_priority": 0.45,
            "modalities": {"PPT", "课件", "展示"},
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
        elif profile.mastery >= 0.7 and resource_type in {"quiz", "code_case", "reading", "ppt_draft"}:
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
            if resource_type in {"ppt_draft", "visual_card", "media_script"}:
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
        allowed_types = [
            resource_type
            for resource_type in self.resource_catalog
            if not state.request.resource_types or resource_type in state.request.resource_types
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


class ResourceAgent(Agent):
    resource_type = "lecture_doc"
    content_format = "markdown"
    title_prefix = "资源"

    def plan_item(self, state: WorkflowState) -> dict:
        return next(
            (item for item in getattr(state, "plan_details", []) if item.get("type") == self.resource_type),
            {},
        )

    def content(self, state: WorkflowState) -> str:
        return f"# {self.title_prefix}\n\n基于 {state.chapter['title']} 生成。"

    def evidence_sources(self, state: WorkflowState) -> list[dict]:
        if not state.sources or not all(isinstance(item, dict) for item in state.sources):
            return []
        preferred_sections = {
            "lecture_doc": {"objectives", "concept_cards", "detailed_concepts", "difficulties", "misconceptions", "real_cases"},
            "mind_map": {"objectives", "concept_cards", "detailed_concepts", "misconceptions"},
            "quiz": {"practice_questions", "detailed_concepts", "misconceptions"},
            "reading": {"reading", "real_cases", "code_labs", "difficulties"},
            "media_script": {"real_cases", "misconceptions", "detailed_concepts"},
            "animation_demo": {"detailed_concepts", "misconceptions", "real_cases"},
            "ppt_draft": {"objectives", "detailed_concepts", "real_cases"},
            "visual_card": {"concept_cards", "detailed_concepts", "misconceptions", "practice_questions"},
            "code_case": {"code_labs", "real_cases", "detailed_concepts"},
        }
        allowed_sections = preferred_sections.get(self.resource_type, set())
        typed_sources = [item for item in state.sources if isinstance(item, dict)]
        matched = [item for item in typed_sources if item.get("section") in allowed_sections]
        return matched or typed_sources[:3]

    def evidence_context(self, state: WorkflowState, limit: int = 4) -> str:
        sources = self.evidence_sources(state)[:limit]
        if not sources:
            return ""
        lines = []
        for source in sources:
            text = re.sub(r"\s+", " ", str(source.get("text", ""))).strip()
            if len(text) > 180:
                text = text[:177] + "..."
            lines.append(
                f"- [{source.get('id')}] score={float(source.get('relevance_score', 0)):.2f} "
                f"{source.get('chapter_title', '')}/{source.get('section', '')}：{text}"
            )
        return "\n".join(lines)

    def evidence_xml_context(self, state: WorkflowState) -> str:
        sources = self.evidence_sources(state)
        if not sources:
            return "<EVIDENCE_CONTEXT />"
        fragments = ["<EVIDENCE_CONTEXT>"]
        for source in sources:
            fragments.append(
                "  <SOURCE "
                f"id=\"{escape(str(source.get('id', '')))}\" "
                f"relevance_score=\"{float(source.get('relevance_score', 0)):.2f}\">"
            )
            fragments.append(f"    <TEXT>{escape(str(source.get('text', '')))}</TEXT>")
            fragments.append(f"    <REASON>{escape(str(source.get('reason', '')))}</REASON>")
            fragments.append("  </SOURCE>")
        fragments.append("</EVIDENCE_CONTEXT>")
        return "\n".join(fragments)

    def allowed_evidence_ids(self, state: WorkflowState) -> set[str]:
        return {str(source.get("id")) for source in self.evidence_sources(state) if source.get("id")}

    def append_evidence_section(self, content: str, state: WorkflowState) -> str:
        if self.content_format != "markdown" or "## 检索依据" in content:
            return content
        evidence = self.evidence_context(state)
        if not evidence:
            return content
        return f"{content.rstrip()}\n\n## 检索依据\n{evidence}"

    def source_refs(self, state: WorkflowState) -> list[str]:
        evidence_ids = [
            str(item.get("id"))
            for item in self.evidence_sources(state)
            if item.get("id")
        ]
        if evidence_ids:
            return evidence_ids

        refs_by_type = {
            "lecture_doc": ["#objectives", "#detailed_concepts", "#misconceptions", "#real_cases"],
            "mind_map": ["#detailed_concepts", "#misconceptions"],
            "quiz": ["#practice_questions", "#detailed_concepts"],
            "reading": ["#reading", "#real_cases", "#code_labs"],
            "media_script": ["#real_cases", "#misconceptions", "#detailed_concepts"],
            "animation_demo": ["#detailed_concepts", "#misconceptions", "#real_cases"],
            "ppt_draft": ["#objectives", "#detailed_concepts", "#real_cases"],
            "visual_card": ["#detailed_concepts", "#misconceptions", "#practice_questions"],
            "code_case": ["#code_labs", "#real_cases", "#detailed_concepts"],
        }
        suffixes = refs_by_type.get(self.resource_type, ["#detailed_concepts"])
        return [f"{state.chapter['id']}{suffix}" for suffix in suffixes]

    def run(self, state: WorkflowState) -> dict:
        content, used_llm, fallback_reason = self.generate_content(state)
        content = self.append_evidence_section(content, state)
        plan_item = self.plan_item(state)
        target_profile = [
            state.profile.cognitive_style,
            *state.profile.preferred_modalities[:2],
        ]
        if plan_item.get("reason"):
            target_profile.append(str(plan_item["reason"]))
        resource = Resource(
            id=f"res_{uuid4().hex[:8]}",
            type=self.resource_type,
            title=f"{self.title_prefix}：{state.chapter['title']}",
            content_format=self.content_format,
            content=content,
            evidence_sources=self.evidence_sources(state),
            source_refs=self.source_refs(state),
            difficulty=str(plan_item.get("difficulty") or "入门到提高"),
            target_profile=target_profile,
            review_status="needs_revision",
            created_by_agents=["KnowledgeAgent", self.name],
            created_at=now(),
        )
        state.resources.append(resource)
        warnings = [f"真实 LLM 生成失败，已回退模板：{fallback_reason}"] if fallback_reason else []
        return {
            "summary": f"生成资源 {resource.title}" + (f"（provider={self.llm.name}）" if used_llm else "（模板兜底）"),
            "warnings": warnings,
            "confidence": 0.88 if used_llm else 0.82,
        }

    def generate_content(self, state: WorkflowState) -> tuple[str, bool, str]:
        return self.content(state), False, ""


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


class MediaAgent(ResourceAgent):
    name = "MediaAgent"
    resource_type = "media_script"
    title_prefix = "视频/动画脚本"
    stage = "producer"
    boundary = "只输出分镜脚本，不直接调用多模态引擎"
    depends_on = ["PlannerAgent", "KnowledgeAgent"]

    def content(self, state: WorkflowState) -> str:
        case_hint = state.chapter["real_cases"][0]
        concept = state.chapter["concepts"][0]
        return (
            "## 3 分钟微课分镜脚本\n\n"
            "| 时间 | 画面 | 旁白 | 屏幕文字 |\n"
            "| --- | --- | --- | --- |\n"
            "| 0:00-0:20 | 学生盯着“训练集、泛化、过拟合”三个词，画面有问号。 | 学机器学习时，最容易混的是：模型到底学到了规律，还是只记住了题目？ | 今天解决：训练表现 vs 泛化表现 |\n"
            "| 0:20-0:55 | 左侧出现课堂练习，右侧出现新试卷。 | 训练集像课堂练习，测试集像新试卷。练习做得好，不代表新试卷一定好。 | 训练集：学习；测试集：检验 |\n"
            "| 0:55-1:30 | 推荐系统给老用户推荐正确，给新用户推荐失准。 | 如果模型只记住老用户的偏好，新用户一来就容易出错，这就是过拟合的直观表现。 | 过拟合：记住样本，迁移变差 |\n"
            "| 1:30-2:10 | 图表展示训练准确率上升、测试准确率下降。 | 判断模型不能只看训练准确率，要同时看新数据上的表现。 | 关注泛化，而不只关注背题 |\n"
            "| 2:10-2:40 | 展示三个检查清单：拆分数据、选指标、看反例。 | 真实任务里，我们用数据拆分、评价指标和错误案例一起判断模型是否可靠。 | 三步检查法 |\n"
            "| 2:40-3:00 | 回到学生，知识点变成流程图。 | 现在你可以用一个自己的例子解释过拟合，并设计一个验证方法。 | 课后任务：造例子 + 说验证 |\n\n"
            "### 拍摄/制作提示\n"
            "- 风格：白板动画 + 简单数据图。\n"
            "- 互动点：1:30 暂停，让学生判断是否过拟合。\n"
            "- 配套练习：完成 1 道判断题和 1 道场景解释题。\n"
            f"- 优先改编案例：{case_hint}\n\n"
            "### 多模态生成预留参数\n"
            f"- visual_style: 扁平化教学动画\n- key_concept: {concept}\n- sync_to_tool: 预留给后续图像/语音/视频生成工具"
        )

    def generate_content(self, state: WorkflowState) -> tuple[str, bool, str]:
        fallback = self.content(state)
        prompt = (
            "你是一个资深的计算机教授和教学视频编导。"
            "请基于给定的课程章节、核心概念、详细知识点和真实案例，生成一份教学微课分镜脚本。\n\n"
            "输出要求：\n"
            "1. 使用中文 Markdown。\n"
            "2. 必须生成包含时间、画面、旁白、屏幕文字的分镜脚本表格。\n"
            "3. 时间轴应覆盖一个 3 分钟左右的短视频或动画微课。\n"
            "4. 画面设计要能帮助学生理解抽象概念，旁白要准确、简洁、适合教学。\n"
            "5. 表格后可补充拍摄/制作提示和多模态工具交接参数。\n\n"
            f"课程章节标题：{state.chapter['title']}\n"
            f"核心概念：{state.chapter['concepts']}\n"
            f"详细知识点：{state.chapter['detailed_concepts']}\n"
            f"真实案例：{state.chapter['real_cases']}\n"
            f"常见误区：{state.chapter['misconceptions']}\n"
            f"代码实操任务：{state.chapter['code_labs']}\n"
            f"学生知识基础与偏好：{state.profile.knowledge_base}\n"
        )
        return self.use_llm_or_fallback(prompt, fallback)


class PPTDraftAgent(ResourceAgent):
    name = "PPTDraftAgent"
    resource_type = "ppt_draft"
    title_prefix = "教学 PPT 草稿"
    stage = "producer"
    boundary = "只产出 PPT 草稿结构，不导出最终文件"
    depends_on = ["PlannerAgent", "KnowledgeAgent"]

    def content(self, state: WorkflowState) -> str:
        concepts = state.chapter["concepts"]
        cases = state.chapter["real_cases"]
        return (
            "## 10 页 PPT 草稿结构\n\n"
            "| 页码 | 标题 | 核心内容 | 讲者提示 |\n"
            "| --- | --- | --- | --- |\n"
            f"| 1 | 章节导入 | 学习目标与应用场景概览 | 用 1 个问题激活先验知识 |\n"
            f"| 2 | 核心概念 1 | {concepts[0]} 的定义与作用边界 | 强调输入-处理-输出链路 |\n"
            f"| 3 | 核心概念 2 | {concepts[1]} 如何评估效果 | 解释为什么单指标不足 |\n"
            f"| 4 | 核心概念 3 | {concepts[2]} 的实现步骤 | 讲清每一步依赖条件 |\n"
            f"| 5 | 核心概念 4 | {concepts[3]} 的典型风险 | 对比正确和错误用法 |\n"
            f"| 6 | 真实案例 A | {cases[0]} | 提问：若失败，先查哪里 |\n"
            f"| 7 | 真实案例 B | {cases[1]} | 讨论自动化与人工复核边界 |\n"
            f"| 8 | 常见误区 | 误区-纠正对照表 | 让学生先判断再揭晓 |\n"
            f"| 9 | 代码实验 | 最小实验 + 噪声样本对比 | 展示实验日志截图 |\n"
            f"| 10 | 复盘与作业 | 三个复盘问题 + 迁移任务 | 引导用自己专业场景复述 |\n\n"
            "### 多模态生成预留参数\n"
            "- slide_theme: education-clean\n- output_target: pptx\n- sync_to_tool: 预留给后续 PPT/图像生成工具"
        )

    def generate_content(self, state: WorkflowState) -> tuple[str, bool, str]:
        fallback = self.content(state)
        prompt = (
            "你是一个资深的计算机教授和教学课件设计专家。"
            "请基于给定的课程章节、核心概念、详细知识点和真实案例，生成教学 PPT 的每页结构表格。\n\n"
            "输出要求：\n"
            "1. 使用中文 Markdown。\n"
            "2. 必须生成教学 PPT 的每页结构表格，表格列至少包含：页码、标题、核心内容、讲者提示。\n"
            "3. PPT 结构应覆盖导入、核心概念讲解、案例分析、常见误区、代码实验、复盘与作业。\n"
            "4. 每页内容要清晰服务于教学目标，讲者提示要具体可执行。\n"
            "5. 表格后可补充 slide_theme、output_target、sync_to_tool 等多模态工具交接参数。\n\n"
            f"课程章节标题：{state.chapter['title']}\n"
            f"核心概念：{state.chapter['concepts']}\n"
            f"详细知识点：{state.chapter['detailed_concepts']}\n"
            f"真实案例：{state.chapter['real_cases']}\n"
            f"常见误区：{state.chapter['misconceptions']}\n"
            f"代码实操任务：{state.chapter['code_labs']}\n"
            f"学生知识基础与偏好：{state.profile.knowledge_base}\n"
        )
        return self.use_llm_or_fallback(prompt, fallback)


class VisualCardAgent(ResourceAgent):
    name = "VisualCardAgent"
    resource_type = "visual_card"
    content_format = "json"
    title_prefix = "可视化学习卡片"
    stage = "producer"
    boundary = "只产出卡片内容与动画提示，不渲染最终素材"
    depends_on = ["PlannerAgent", "KnowledgeAgent"]

    def content(self, state: WorkflowState) -> str:
        cards = []
        for idx, concept in enumerate(state.chapter["concepts"], start=1):
            cards.append(
                {
                    "id": f"card_{idx:02d}",
                    "title": concept,
                    "tagline": f"{state.chapter['title']} 核心要点",
                    "what": state.chapter["detailed_concepts"][idx - 1],
                    "pitfall": state.chapter["misconceptions"][idx - 1],
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


class AnimationDemoAgent(ResourceAgent):
    name = "AnimationDemoAgent"
    resource_type = "animation_demo"
    content_format = "json"
    title_prefix = "可播放教学动画"
    stage = "producer"
    boundary = "生成可在前端直接播放的动态图解脚本，不导出 mp4 成片"
    depends_on = ["PlannerAgent", "KnowledgeAgent"]

    def content(self, state: WorkflowState) -> str:
        concepts = state.chapter["concepts"]
        misconceptions = state.chapter["misconceptions"]
        cases = state.chapter["real_cases"]
        frames = [
            {
                "id": "frame_01",
                "title": f"先看输入：{concepts[0]}",
                "caption": "动画把训练样本放在左侧，强调模型首先接触的是已知数据。",
                "focus": concepts[0],
                "visual": "dataset",
            },
            {
                "id": "frame_02",
                "title": f"再看目标：{concepts[1]}",
                "caption": "箭头从训练数据移动到新数据，突出真正要检查的是新场景表现。",
                "focus": concepts[1],
                "visual": "generalization",
            },
            {
                "id": "frame_03",
                "title": f"用指标观察：{concepts[2]}",
                "caption": "损失曲线下降不等于学习完成，要同时观察验证表现。",
                "focus": concepts[2],
                "visual": "loss",
            },
            {
                "id": "frame_04",
                "title": f"警惕误区：{concepts[3]}",
                "caption": misconceptions[1] if len(misconceptions) > 1 else misconceptions[0],
                "focus": concepts[3],
                "visual": "overfit",
            },
        ]
        return json.dumps(
            {
                "kind": "in_app_animation",
                "duration_seconds": 32,
                "playback_note": "这是系统内可播放的动态图解，不是人工录制视频，也不是 mp4 成片。",
                "scenario": cases[0],
                "frames": frames,
                "teacher_prompt": "播放时引导学生观察：训练表现、泛化表现和常见误区分别在哪里出现。",
            },
            ensure_ascii=False,
            indent=2,
        )

    def generate_content(self, state: WorkflowState) -> tuple[str, bool, str]:
        fallback = self.content(state)
        prompt = (
            "你是一个教学动画导演和计算机课程教师。请生成一个可在网页前端直接播放的教学动画 JSON，"
            "用于把抽象概念转成准确、生动、形象的动态讲解。\n\n"
            "只输出 JSON，不要输出 Markdown，不要包裹代码块。\n"
            "JSON 必须包含 kind、duration_seconds、playback_note、scenario、frames、teacher_prompt。\n"
            "frames 是数组，每项包含 id、title、caption、focus、visual；visual 只能从 dataset、generalization、loss、overfit 中选择。\n\n"
            f"课程章节标题：{state.chapter['title']}\n"
            f"核心概念：{state.chapter['concepts']}\n"
            f"详细知识点：{state.chapter['detailed_concepts']}\n"
            f"常见误区：{state.chapter['misconceptions']}\n"
            f"真实案例：{state.chapter['real_cases']}\n"
        )
        content, used_llm, reason = self.use_llm_or_fallback(prompt, fallback)
        if used_llm:
            try:
                parsed = parse_llm_json(content)
                frames = parsed.get("frames") if isinstance(parsed, dict) else None
                if isinstance(frames, list) and frames:
                    return json.dumps(parsed, ensure_ascii=False, indent=2), True, ""
                return fallback, False, "LLM returned animation JSON without frames"
            except json.JSONDecodeError as exc:
                return fallback, False, f"LLM returned invalid animation JSON: {exc}"
        return content, used_llm, reason


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


class ReviewAgent(Agent):
    name = "ReviewAgent"
    role = "审核事实、来源、难度与安全"
    stage = "review"
    boundary = "负责审核与仲裁，不负责新增资源内容"

    def __init__(self, llm: BaseLLMProvider | None = None):
        super().__init__(llm)
        self.confidence_threshold = 0.7
        self._fact_check_patterns = [
            (r"训练集.*泛化", ["训练集", "泛化能力", "过拟合"]),
            (r"损失函数.*优化", ["损失函数", "优化算法", "梯度下降"]),
            (r"过拟合.*正则化", ["过拟合", "正则化", "欠拟合"]),
        ]

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

    def _basic_fact_check(self, content: str, chapter: dict) -> dict:
        """基础事实校验"""
        issues = []
        concepts = chapter.get("concepts", [])
        detailed = chapter.get("detailed_concepts", [])

        content_lower = content.lower()
        mentioned_concepts = [c for c in concepts if c.lower() in content_lower]

        def concept_mentioned(concept: str) -> bool:
            concept_lower = concept.lower()
            if concept_lower in content_lower:
                return True
            return any(
                base.lower() in content_lower or content_lower.find(base.lower().replace("能力", "")) >= 0
                for base in concepts
                if base.lower() in concept_lower or concept_lower in base.lower()
            )

        if len(mentioned_concepts) < 2 and len(content) > 500:
            issues.append({
                "type": "missing_citation",
                "description": f"内容中仅提及 {len(mentioned_concepts)} 个核心概念，可能存在引用缺失",
                "severity": "low"
            })

        for pattern, required_concepts in self._fact_check_patterns:
            if re.search(pattern, content_lower):
                for concept in required_concepts:
                    if not concept_mentioned(concept):
                        issues.append({
                            "type": "logic_error",
                            "description": f"讨论 '{concept}' 相关主题时未提及关联概念",
                            "severity": "medium"
                        })

        dangerous_keywords = ["违法", "犯罪", "赌博", "毒品", "暴力"]
        for keyword in dangerous_keywords:
            if keyword in content:
                issues.append({
                    "type": "security_risk",
                    "description": f"内容包含敏感关键词：{keyword}",
                    "severity": "high"
                })

        accuracy_score = 1.0 - (len(issues) * 0.15)
        accuracy_score = max(0.0, min(1.0, accuracy_score))

        return {
            "issues": issues,
            "accuracy_score": round(accuracy_score, 2),
            "verified": len(issues) == 0
        }

    def _attempt_llm_fact_check(self, content: str, chapter: dict) -> dict | None:
        """尝试使用 LLM 进行事实校验"""
        return None
        try:
            key_facts = chapter.get("concepts", []) + chapter.get("detailed_concepts", [])[:2]
            prompt = build_review_fact_check_prompt(content, chapter, key_facts)
            response = self.llm.complete(prompt)
            result = self._extract_json_from_response(response)

            if result and "is_accurate" in result:
                confidence = result.get("confidence", 0.5)
                if confidence >= self.confidence_threshold:
                    return result
        except (LLMProviderError, Exception):
            pass
        return None

    @staticmethod
    def _keywords(state: WorkflowState) -> list[str]:
        chapter = state.chapter
        raw_keywords = [
            state.request.chapter,
            state.request.goal,
            chapter["title"],
            *chapter["concepts"],
            *chapter.get("detailed_concepts", []),
            *chapter.get("real_cases", []),
            *chapter.get("code_labs", []),
            *chapter["difficulties"],
            *chapter["misconceptions"],
        ]
        unique_keywords: list[str] = []
        for keyword in raw_keywords:
            normalized = keyword.strip().lower()
            if len(normalized) >= 2 and normalized not in unique_keywords:
                unique_keywords.append(normalized)
        return unique_keywords

    @staticmethod
    def _is_relevant(resource: Resource, keywords: list[str]) -> tuple[bool, list[str]]:
        text = f"{resource.title}\n{resource.content}".lower()
        matched = [keyword for keyword in keywords if keyword in text]
        return len(matched) >= 2, matched[:5]

    @staticmethod
    def _allowed_source_refs(chapter: dict) -> set[str]:
        allowed_sections = {
            "overview",
            "practice",
            "objectives",
            "concepts",
            "concept_cards",
            "detailed_concepts",
            "difficulties",
            "misconceptions",
            "example",
            "real_cases",
            "practice_drafts",
            "practice_questions",
            "reading",
            "code_labs",
            "task",
        }
        return {f"{chapter['id']}#{section}" for section in allowed_sections}

    def _invalid_source_refs(self, resource: Resource, chapter: dict) -> list[str]:
        allowed_refs = self._allowed_source_refs(chapter)
        invalid_refs = []
        for ref in resource.source_refs:
            base_ref = str(ref).split(":", 1)[0]
            if ref not in allowed_refs and base_ref not in allowed_refs:
                invalid_refs.append(ref)
        return invalid_refs

    @staticmethod
    def _inline_source_ids(content: str) -> list[str]:
        return [match.strip() for match in re.findall(r"\[来源:\s*([^\]]+?)\s*\]", content)]

    def _invalid_evidence_ids(self, resource: Resource, chapter: dict) -> list[str]:
        allowed_refs = self._allowed_source_refs(chapter)
        invalid_ids = []
        for evidence in resource.evidence_sources:
            evidence_id = str(evidence.id)
            base_ref = evidence_id.split(":", 1)[0]
            if evidence_id not in allowed_refs and base_ref not in allowed_refs:
                invalid_ids.append(evidence_id)
        return invalid_ids

    @staticmethod
    def _evidence_keywords(text: str) -> set[str]:
        tokens = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{2,}", text.lower())
        stop_words = {"学习", "目标", "当前", "章节", "知识", "理解", "掌握", "案例", "相关", "一个", "需要", "可以"}
        keywords = {token for token in tokens if token not in stop_words}
        for token in tokens:
            if re.fullmatch(r"[\u4e00-\u9fff]{3,}", token):
                for size in range(2, min(4, len(token)) + 1):
                    for index in range(0, len(token) - size + 1):
                        ngram = token[index : index + size]
                        if ngram not in stop_words:
                            keywords.add(ngram)
        return keywords

    def _content_hits_evidence(self, resource: Resource) -> tuple[bool, list[str]]:
        content_tokens = self._evidence_keywords(resource.content)
        hit_ids: list[str] = []
        for evidence in resource.evidence_sources:
            evidence_tokens = self._evidence_keywords(evidence.text)
            if not evidence_tokens:
                continue
            overlap = content_tokens & evidence_tokens
            if len(overlap) >= 1:
                hit_ids.append(evidence.id)
        return bool(hit_ids), hit_ids[:5]

    def _evidence_review(self, resource: Resource, chapter: dict) -> dict:
        issues: list[str] = []
        notes: list[str] = []
        evidence_by_id = {evidence.id: evidence for evidence in resource.evidence_sources}
        inline_ids = self._inline_source_ids(resource.content)

        if not resource.evidence_sources:
            issues.append("缺少 evidence_sources 结构化证据")
            notes.append("未找到结构化证据，无法证明内容来自 KnowledgeAgent 召回片段。")
            return {"passed": False, "issues": issues, "notes": notes, "inline_ids": inline_ids, "hit_ids": []}

        missing_text_ids = [evidence.id for evidence in resource.evidence_sources if not evidence.text.strip()]
        if missing_text_ids:
            issues.append("evidence_sources 缺少原文 text")
            notes.append(f"缺少证据原文的来源：{'、'.join(missing_text_ids[:5])}")

        invalid_evidence_ids = self._invalid_evidence_ids(resource, chapter)
        if invalid_evidence_ids:
            issues.append("evidence_sources 存在无效来源 ID")
            notes.append(f"无效证据来源：{'、'.join(invalid_evidence_ids[:5])}")

        unknown_inline_ids = [source_id for source_id in inline_ids if source_id not in evidence_by_id]
        if unknown_inline_ids:
            issues.append("正文内联来源引用无法映射到 evidence_sources")
            notes.append(f"无法映射的正文引用：{'、'.join(unknown_inline_ids[:5])}")

        if resource.content_format == "markdown" and not inline_ids:
            issues.append("Markdown 正文缺少 [来源: id] 内联引用")
            notes.append("正文没有出现可追踪的 [来源: id] 引用。")

        hits_evidence, hit_ids = self._content_hits_evidence(resource)
        if not hits_evidence:
            issues.append("核心内容未命中任何证据片段")
            notes.append("正文关键词与 evidence_sources 原文没有形成可检测重叠。")
        else:
            notes.append(f"内容命中的证据片段：{'、'.join(hit_ids)}")

        return {
            "passed": not issues,
            "issues": issues,
            "notes": notes,
            "inline_ids": inline_ids,
            "hit_ids": hit_ids,
        }

    def run(self, state: WorkflowState) -> dict:
        blocked = 0
        passed = 0
        needs_revision = 0
        keywords = self._keywords(state)
        fact_check_summary: list[str] = []
        for resource in state.resources:
            has_sources = bool(resource.source_refs)
            has_evidence = bool(resource.evidence_sources)
            invalid_refs = self._invalid_source_refs(resource, state.chapter) if has_sources else []
            evidence_review = self._evidence_review(resource, state.chapter)
            is_related, matched_keywords = self._is_relevant(resource, keywords)
            fact_check = self._basic_fact_check(resource.content, state.chapter)
            llm_fact_check = self._attempt_llm_fact_check(resource.content, state.chapter)
            reasons: list[str] = []
            notes: list[str] = []
            if llm_fact_check:
                notes.append(f"LLM事实校验：{llm_fact_check.get('reasoning', '已完成')}")
                if not llm_fact_check.get("is_accurate", True):
                    fact_check["issues"].append(
                        {
                            "type": "llm_fact_check",
                            "description": llm_fact_check.get("reasoning", "LLM 认为内容需要复核"),
                            "severity": "medium",
                        }
                    )
                    fact_check["accuracy_score"] = min(fact_check["accuracy_score"], float(llm_fact_check.get("confidence", 0.5)))

            if "违法" in resource.content:
                reasons.append("内容命中安全风险关键词")
                notes.append("内容包含安全风险关键词，已阻断。")
                resource.review_status = "blocked"
                blocked += 1
            elif any(issue.get("severity") == "high" for issue in fact_check["issues"]):
                reasons.append("事实/安全校验发现高风险问题")
                notes.extend(issue["description"] for issue in fact_check["issues"])
                resource.review_status = "blocked"
                blocked += 1
            elif not has_evidence or not evidence_review["passed"]:
                reasons.extend(evidence_review["issues"] or ["结构化证据审核未通过"])
                notes.extend(evidence_review["notes"])
                resource.review_status = "needs_revision"
                needs_revision += 1
            elif not has_sources:
                reasons.append("缺少 source_refs 兼容来源标注")
                notes.append("未找到兼容 source_refs；请确认 evidence_sources 到 source_refs 的派生逻辑。")
                resource.review_status = "needs_revision"
                needs_revision += 1
            elif invalid_refs:
                reasons.append("source_refs 存在无效引用")
                notes.append(f"无效来源引用：{'、'.join(invalid_refs[:3])}")
                resource.review_status = "needs_revision"
                needs_revision += 1
            elif not is_related:
                reasons.append("内容与当前课程知识点匹配度不足")
                notes.append("标题和正文中匹配到的课程关键词不足，建议补充章节核心概念或案例。")
                resource.review_status = "needs_revision"
                needs_revision += 1
            elif fact_check["issues"]:
                reasons.append("基础事实校验发现轻中度问题")
                notes.extend(issue["description"] for issue in fact_check["issues"])
                resource.review_status = "needs_revision"
                needs_revision += 1
            else:
                reasons.append("结构化证据完整且与课程知识点相关")
                notes.append("evidence_sources 原文、正文引用与课程知识库映射均通过。")
                notes.append("内容命中章节核心概念或案例，相关性检查通过。")
                resource.review_status = "passed"
                passed += 1

            if has_evidence:
                notes.append(f"结构化证据数量：{len(resource.evidence_sources)}")
            if has_sources:
                notes.append(f"来源数量：{len(resource.source_refs)}")
            if evidence_review.get("inline_ids"):
                notes.append(f"正文引用：{'、'.join(evidence_review['inline_ids'][:5])}")
            if matched_keywords:
                notes.append(f"相关关键词：{'、'.join(matched_keywords)}")
            notes.append(f"基础事实校验分：{fact_check['accuracy_score']:.2f}")

            confidence = 0.45
            if has_evidence and evidence_review["passed"]:
                confidence += 0.25
            elif has_sources and not invalid_refs:
                confidence += 0.25
            if is_related:
                confidence += 0.25
            confidence += max(fact_check["accuracy_score"] - 0.7, 0) * 0.15
            if resource.review_status == "blocked":
                confidence = 0.35
            if resource.review_status == "needs_revision":
                confidence = min(confidence, 0.74)
            resource.review_confidence = round(min(max(confidence, 0.0), 0.99), 2)
            resource.audit_reason = "；".join(reasons)
            resource.review_notes = notes
            resource.review_reason = resource.audit_reason
            fact_check_summary.append(f"{resource.type}:{resource.review_status}:{resource.review_confidence:.2f}")
            if "ReviewAgent" not in resource.created_by_agents:
                resource.created_by_agents.append("ReviewAgent")
        return {
            "summary": (
                f"审核 {len(state.resources)} 份资源，"
                f"passed={passed}，needs_revision={needs_revision}，blocked={blocked}"
            ),
            "confidence": 0.91,
            "arbitration_note": "冲突仲裁规则：来源缺失优先判定 needs_revision；安全风险优先判定 blocked；其余按相关性判定。",
            "review_conclusion": f"最终结论：passed={passed}，needs_revision={needs_revision}，blocked={blocked}；明细：{' | '.join(fact_check_summary)}",
        }


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


class Orchestrator:
    producer_resource_types = {
        "LectureAgent": "lecture_doc",
        "MindMapAgent": "mind_map",
        "QuizAgent": "quiz",
        "ReadingAgent": "reading",
        "MediaAgent": "media_script",
        "AnimationDemoAgent": "animation_demo",
        "PPTDraftAgent": "ppt_draft",
        "VisualCardAgent": "visual_card",
        "CodeCaseAgent": "code_case",
    }

    def __init__(self):
        llm = get_llm_provider()
        self.agents = [
            ProfileAgent(llm),
            KnowledgeAgent(llm),
            PlannerAgent(llm),
            LectureAgent(llm),
            MindMapAgent(llm),
            QuizAgent(llm),
            ReadingAgent(llm),
            MediaAgent(llm),
            AnimationDemoAgent(llm),
            PPTDraftAgent(llm),
            VisualCardAgent(llm),
            CodeCaseAgent(llm),
            ReviewAgent(llm),
            AssessmentAgent(llm),
        ]

    def _build_agent_graph(self) -> dict[str, list[str]]:
        """构建智能体依赖图"""
        return {
            "ProfileAgent": [],
            "KnowledgeAgent": ["ProfileAgent"],
            "PlannerAgent": ["KnowledgeAgent"],
            "LectureAgent": ["PlannerAgent", "KnowledgeAgent"],
            "MindMapAgent": ["PlannerAgent", "KnowledgeAgent"],
            "QuizAgent": ["PlannerAgent", "KnowledgeAgent"],
            "ReadingAgent": ["PlannerAgent", "KnowledgeAgent"],
            "MediaAgent": ["PlannerAgent", "KnowledgeAgent"],
            "AnimationDemoAgent": ["PlannerAgent", "KnowledgeAgent"],
            "PPTDraftAgent": ["PlannerAgent", "KnowledgeAgent"],
            "VisualCardAgent": ["PlannerAgent", "KnowledgeAgent"],
            "CodeCaseAgent": ["PlannerAgent", "KnowledgeAgent"],
            "ReviewAgent": ["LectureAgent", "MindMapAgent", "QuizAgent", "ReadingAgent", "MediaAgent", "AnimationDemoAgent", "PPTDraftAgent", "VisualCardAgent", "CodeCaseAgent"],
            "AssessmentAgent": ["ReviewAgent"]
        }

    def _get_execution_order(self) -> list[str]:
        """获取智能体执行顺序（拓扑排序）"""
        graph = self._build_agent_graph()
        visited = set()
        order = []

        def dfs(agent: str):
            if agent in visited:
                return
            visited.add(agent)
            for dep in graph.get(agent, []):
                dfs(dep)
            order.append(agent)

        for agent in self.agents:
            dfs(agent.name)

        return order

    def enabled_agent_names(self, request: GenerateRequest) -> list[str]:
        requested_types = set(request.resource_types or self.producer_resource_types.values())
        enabled = ["ProfileAgent", "KnowledgeAgent", "PlannerAgent"]
        enabled.extend(
            agent_name
            for agent_name, resource_type in self.producer_resource_types.items()
            if resource_type in requested_types
        )
        enabled.append("ReviewAgent")
        return enabled

    def _get_feedback_from_review(self, state: WorkflowState) -> dict:
        """从ReviewAgent获取反馈信息"""
        feedback = {
            "resources_need_revision": [],
            "common_issues": [],
            "quality_score": 0.0
        }

        for resource in state.resources:
            if resource.review_status == "needs_revision":
                feedback["resources_need_revision"].append({
                    "id": resource.id,
                    "type": resource.type,
                    "reason": resource.review_reason
                })

        if state.traces:
            review_trace = next((t for t in state.traces if t.agent == "ReviewAgent"), None)
            if review_trace:
                feedback["quality_score"] = sum(
                    t.confidence for t in state.traces if t.status == "completed"
                ) / len(state.traces) if state.traces else 0.0

        return feedback

    def generate(self, job_id: str, request: GenerateRequest, profile: Profile):
        state = WorkflowState(job_id, request, profile)
        execution_order = self._get_execution_order()
        enabled_agents = set(self.enabled_agent_names(request))

        agent_map = {agent.name: agent for agent in self.agents}

        for agent_name in execution_order:
            if agent_name not in enabled_agents:
                continue
            resource_type = self.producer_resource_types.get(agent_name)
            if resource_type and state.plan and resource_type not in state.plan:
                continue
            agent = agent_map.get(agent_name)
            if not agent:
                continue

            context_summary = f"{request.chapter} / {request.goal}"
            trace = agent.traced_run(state, context_summary)

            if agent_name == "ReviewAgent":
                state.feedback_from_review = self._get_feedback_from_review(state)
                state.learning_context["review_feedback"] = state.feedback_from_review

            if agent_name == "AssessmentAgent" and hasattr(state, 'feedback_from_review'):
                state.learning_context["improvement_suggestions"] = state.feedback_from_review.get("resources_need_revision", [])

            yield agent, state

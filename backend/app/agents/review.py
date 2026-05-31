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
            if concept_lower.endswith("能力") and concept_lower.removesuffix("能力") in content_lower:
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
        if self.llm.name == "mock":
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
        text = ReviewAgent._normalize_text_for_review(f"{resource.title}\n{resource.content}")
        normalized_keywords = [ReviewAgent._normalize_text_for_review(keyword) for keyword in keywords]
        matched = [keyword for keyword in normalized_keywords if keyword and keyword in text]
        if len(matched) >= 2:
            return True, matched[:5]

        text_tokens = ReviewAgent._evidence_keywords(text)
        token_matches: list[str] = []
        for keyword in normalized_keywords:
            keyword_tokens = ReviewAgent._evidence_keywords(keyword)
            for token in sorted(text_tokens & keyword_tokens):
                if token not in token_matches:
                    token_matches.append(token)
        return len(token_matches) >= 2, token_matches[:5]

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

    SOURCE_CITATION_RE = re.compile(r"\[(?:来源|鏉ユ簮|[^\]:]{1,8}):\s*([^\]]+?)\s*\]")

    @staticmethod
    def _normalize_text_for_review(text: str) -> str:
        variants = {text}
        for source_encoding in ("latin1", "cp1252"):
            try:
                variants.add(text.encode(source_encoding).decode("utf-8"))
            except UnicodeError:
                continue
        return " ".join(variants).lower()

    @classmethod
    def _inline_source_ids(cls, content: str) -> list[str]:
        return [match.strip() for match in cls.SOURCE_CITATION_RE.findall(content)]

    @classmethod
    def _inline_source_matches(cls, content: str) -> list[tuple[str, int, int]]:
        return [
            (match.group(1).strip(), match.start(), match.end())
            for match in cls.SOURCE_CITATION_RE.finditer(content)
        ]

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
        normalized = ReviewAgent._normalize_text_for_review(text)
        tokens = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{2,}", normalized)
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

    def _evidence_overlap_report(self, resource: Resource) -> dict:
        content_tokens = self._evidence_keywords(resource.content)
        evidence_tokens_by_id = {
            evidence.id: self._evidence_keywords(evidence.text)
            for evidence in resource.evidence_sources
            if evidence.text.strip()
        }
        evidence_tokens = set().union(*evidence_tokens_by_id.values()) if evidence_tokens_by_id else set()
        overlap = content_tokens & evidence_tokens
        denominator = max(min(len(content_tokens), 30), 1)
        coverage_score = min(1.0, len(overlap) / denominator)
        weak_inline_ids: list[str] = []
        inline_overlaps: dict[str, list[str]] = {}

        for source_id, start, end in self._inline_source_matches(resource.content):
            evidence_tokens_for_id = evidence_tokens_by_id.get(source_id, set())
            if not evidence_tokens_for_id:
                continue
            window = resource.content[max(0, start - 60) : min(len(resource.content), end + 60)]
            window_overlap = self._evidence_keywords(window) & evidence_tokens_for_id
            inline_overlaps[source_id] = sorted(window_overlap)[:8]
            if len(window_overlap) < 2:
                weak_inline_ids.append(source_id)

        return {
            "coverage_score": round(coverage_score, 2),
            "overlap_keywords": sorted(overlap)[:10],
            "weak_inline_ids": weak_inline_ids,
            "inline_overlaps": inline_overlaps,
        }

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

        overlap_report = self._evidence_overlap_report(resource)
        if overlap_report["coverage_score"] < 0.08:
            issues.append("正文与证据关键词重叠不足")
            notes.append(f"证据覆盖分过低：{overlap_report['coverage_score']:.2f}")
        else:
            notes.append(f"证据覆盖分：{overlap_report['coverage_score']:.2f}")
        if overlap_report["overlap_keywords"]:
            notes.append(f"证据重叠关键词：{'、'.join(overlap_report['overlap_keywords'][:8])}")

        if overlap_report["weak_inline_ids"]:
            issues.append("正文引用附近未命中对应证据")
            notes.append(f"引用附近缺少对应证据支撑：{'、'.join(overlap_report['weak_inline_ids'][:5])}")

        return {
            "passed": not issues,
            "issues": issues,
            "notes": notes,
            "inline_ids": inline_ids,
            "hit_ids": hit_ids,
            "coverage_score": overlap_report["coverage_score"],
            "overlap_keywords": overlap_report["overlap_keywords"],
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
            if (
                not is_related
                and evidence_review.get("passed")
                and len(evidence_review.get("hit_ids", [])) >= 2
            ):
                is_related = True
                matched_keywords = list(evidence_review.get("overlap_keywords", []))[:5]
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

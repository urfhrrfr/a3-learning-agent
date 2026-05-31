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
            "html_ppt": {"objectives", "detailed_concepts", "real_cases"},
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
            "html_ppt": ["#objectives", "#detailed_concepts", "#real_cases"],
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
            *state.request.target_concepts[:3],
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
            personalized_reason=(
                f"本次需求：{state.request.raw_user_need or state.request.goal}；"
                f"匹配章节：{state.chapter['title']}；"
                f"匹配置信度：{state.request.chapter_match_confidence:.2f}；"
                f"目标概念：{'、'.join(state.request.target_concepts) or '按章节核心概念'}。"
            ),
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

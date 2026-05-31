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

from .profile import ProfileAgent
from .knowledge import KnowledgeAgent
from .planner import PlannerAgent
from .resources.lecture import LectureAgent
from .resources.mind_map import MindMapAgent
from .resources.quiz import QuizAgent
from .resources.reading import ReadingAgent
from .resources.media import MediaAgent
from .resources.animation import AnimationDemoAgent
from .resources.ppt import PPTDraftAgent
from .resources.visual_card import VisualCardAgent
from .resources.code_case import CodeCaseAgent
from .review import ReviewAgent
from .assessment import AssessmentAgent


class Orchestrator:
    producer_resource_types = {
        "LectureAgent": "lecture_doc",
        "MindMapAgent": "mind_map",
        "QuizAgent": "quiz",
        "ReadingAgent": "reading",
        "MediaAgent": "media_script",
        "AnimationDemoAgent": "animation_demo",
        "PPTDraftAgent": "html_ppt",
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

            context_summary = f"{request.chapter} / {request.raw_user_need or request.goal}"
            trace = agent.traced_run(state, context_summary)

            if agent_name == "ReviewAgent":
                state.feedback_from_review = self._get_feedback_from_review(state)
                state.learning_context["review_feedback"] = state.feedback_from_review

            if agent_name == "AssessmentAgent" and hasattr(state, 'feedback_from_review'):
                state.learning_context["improvement_suggestions"] = state.feedback_from_review.get("resources_need_revision", [])

            yield agent, state

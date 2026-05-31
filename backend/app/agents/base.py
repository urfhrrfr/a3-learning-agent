from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from uuid import uuid4

from ..knowledge import find_chapter
from ..providers.base import BaseLLMProvider, LLMProviderError
from ..providers.factory import get_llm_provider
from ..schemas import AgentTrace, GenerateRequest, Profile, Resource


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
        self.current_query = "；".join(
            item
            for item in [
                request.raw_user_need,
                request.goal,
                request.chapter,
                "、".join(request.target_concepts or []),
                "、".join(request.pain_points or []),
            ]
            if item
        )
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

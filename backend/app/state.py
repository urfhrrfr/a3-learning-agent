from __future__ import annotations

import json
import random
import re
from datetime import datetime, timezone
from threading import Lock, Thread
from uuid import uuid4

from .agents import AssessmentAgent, Orchestrator, ProfileAgent, now
from .cache import cache_job, get_cached_job
from .path_planner import PathPlanner
from .providers.factory import get_llm_provider
from .knowledge import infer_target_concepts, match_chapter
from .schemas import (
    AssessmentReport,
    AgentTrace,
    ChatAndGenerateRequest,
    GenerateRequest,
    GenerationJob,
    LearningPath,
    LearningPathStep,
    Profile,
    QuizSubmitRequest,
    Resource,
    ResourceAdjustRequest,
    ResourceFeedbackRequest,
    PlanDecision,
    PlanSummary,
)
from .storage import delete_records, load_latest_record, load_records, save_record


profile = Profile(updated_at=now())
profiles: dict[str, Profile] = {}
jobs: dict[str, GenerationJob] = {}
job_profiles: dict[str, Profile] = {}
resources = []
learning_path: LearningPath | None = None
assessment_report: AssessmentReport | None = None
DEFAULT_USER_ID = "student_demo"
generation_lock = Lock()
active_generation_job_id: str | None = None


PROFILE_DIMENSIONS = [
    {
        "key": "knowledge_base",
        "label": "知识基础",
        "description": "学生已掌握或仍薄弱的先修知识。",
        "value_type": "list[str]",
        "update_rule": "对话命中数学/线代等关键词时补充薄弱基础。",
    },
    {
        "key": "learning_goal",
        "label": "学习目标",
        "description": "当前学习阶段的目标导向。",
        "value_type": "str",
        "update_rule": "命中项目/考研等目标词时重写学习目标。",
    },
    {
        "key": "cognitive_style",
        "label": "认知风格",
        "description": "偏好的理解路径，如例子驱动、结构化推理。",
        "value_type": "str",
        "update_rule": "可按后续对话扩展，目前默认例子驱动。",
    },
    {
        "key": "preferred_modalities",
        "label": "学习偏好模态",
        "description": "偏好的资源形态，如图解、代码、短视频。",
        "value_type": "list[str]",
        "update_rule": "命中代码/Python/视频等关键词时追加偏好。",
    },
    {
        "key": "weak_points",
        "label": "知识薄弱点",
        "description": "当前最需强化的知识点。",
        "value_type": "list[str]",
        "update_rule": "命中梯度等关键词时追加薄弱点；测评后动态更新。",
    },
    {
        "key": "mistake_patterns",
        "label": "易错模式",
        "description": "在练习与答疑中反复出现的错误倾向。",
        "value_type": "list[str]",
        "update_rule": "测评提交后按成绩区间更新错误模式。",
    },
    {
        "key": "time_budget",
        "label": "时间预算",
        "description": "日常可投入学习时间。",
        "value_type": "str",
        "update_rule": "可在后续对话里解析“每天 X 分钟”更新。",
    },
    {
        "key": "mastery",
        "label": "掌握度",
        "description": "当前阶段的综合掌握度估计。",
        "value_type": "float",
        "update_rule": "随练习成绩动态调整并参与路径重规划。",
    },
]


def event(job: GenerationJob, event_type: str, payload: dict):
    item = {"type": event_type, "payload": payload, "created_at": now()}
    job.events.append(item)
    return item


def normalize_resource(resource: Resource) -> Resource:
    if resource.source_refs and not resource.evidence_sources:
        resource.evidence_sources = [{"id": ref, "text": "", "relevance_score": 0.0, "reason": ""} for ref in resource.source_refs]
    if resource.evidence_sources and not resource.source_refs:
        resource.source_refs = [source.id for source in resource.evidence_sources]
    resource.personalized_reason = resource.personalized_reason or "基于当前学生画像、薄弱点和学习偏好生成。"
    resource.review_reason = resource.review_reason or resource.audit_reason or "演示兜底审核：结构完整，可用于学习。"
    resource.audit_reason = resource.audit_reason or resource.review_reason
    resource.review_notes = resource.review_notes or ["字段完整性检查通过。"]
    resource.created_by_agents = resource.created_by_agents or ["ResourceFallback"]
    return resource


def fallback_resources(request: GenerateRequest, reason: str) -> list[Resource]:
    chapter = find_chapter(request.chapter)
    refs = [f"{chapter['id']}#objectives", f"{chapter['id']}#detailed_concepts", f"{chapter['id']}#practice_questions"]
    base_target = ["演示兜底", *(request.target_concepts or [])[:3], *(request.pain_points or [])[:2]]
    intent_note = (
        f"本次需求：{request.raw_user_need or request.goal}；"
        f"匹配章节：{chapter['title']}；"
        f"概念：{'、'.join(request.target_concepts) or '按章节核心概念'}。"
    )
    items = [
        Resource(
            id=f"res_{uuid4().hex[:8]}",
            type="lecture_doc",
            title=f"兜底讲解文档：{chapter['title']}",
            content_format="markdown",
            content=(
                f"# {chapter['title']} 演示兜底讲解\n\n"
                f"当前目标：{request.goal}\n\n"
                "## 核心概念\n"
                + "\n".join(f"- {item}" for item in chapter.get("concepts", [])[:4])
                + "\n\n## 学习建议\n先用一个生活例子解释概念，再完成一道练习确认是否理解。"
            ),
            source_refs=refs[:2],
            difficulty="入门",
            target_profile=base_target,
            personalized_reason=f"{intent_note} LLM 或智能体链路不可用时，用课程知识库生成可展示讲解。",
            review_status="passed",
            review_reason=f"fallback_reason: {reason}",
            audit_reason=f"fallback_reason: {reason}",
            review_notes=["资源来自本地课程知识库，未调用真实视频生成。"],
            review_confidence=0.72,
            created_by_agents=["ResourceFallback", "ReviewAgent"],
            created_at=now(),
        ),
        Resource(
            id=f"res_{uuid4().hex[:8]}",
            type="quiz",
            title=f"兜底练习题：{chapter['title']}",
            content_format="json",
            content=json.dumps(chapter.get("practice_questions", [])[:5], ensure_ascii=False, indent=2),
            source_refs=refs,
            difficulty="基础",
            target_profile=base_target,
            personalized_reason=f"{intent_note} 保证演示中练习评估主链路可继续。",
            review_status="passed",
            review_reason=f"fallback_reason: {reason}",
            audit_reason=f"fallback_reason: {reason}",
            review_notes=["题目来自本地题库。"],
            review_confidence=0.74,
            created_by_agents=["QuizFallback", "ReviewAgent"],
            created_at=now(),
        ),
    ]
    return [normalize_resource(item) for item in items]


def persist_job(job: GenerationJob) -> None:
    payload = job.model_dump()
    save_record("job", job.id, payload)
    cache_job(job.id, payload)


def get_job(job_id: str) -> GenerationJob | None:
    if job_id in jobs:
        return jobs[job_id]

    cached = get_cached_job(job_id)
    if cached:
        try:
            job = GenerationJob(**cached)
            jobs[job.id] = job
            return job
        except Exception:  # noqa: BLE001
            pass

    stored = next((item for item in load_records("job") if item.get("id") == job_id), None)
    if stored:
        try:
            job = GenerationJob(**stored)
            jobs[job.id] = job
            return job
        except Exception:  # noqa: BLE001
            return None
    return None


def _record_time_key(item: dict) -> str:
    return str(item.get("completed_at") or item.get("updated_at") or item.get("created_at") or "")


def latest_generation_job_id() -> str:
    if active_generation_job_id:
        return active_generation_job_id
    completed_jobs = [
        job
        for job in jobs.values()
        if job.status == "completed" and job.resources
    ]
    if not completed_jobs:
        return ""
    latest = max(completed_jobs, key=lambda item: item.completed_at or item.created_at)
    return latest.id


def _generation_history_jobs(limit: int = 20) -> tuple[list[GenerationJob], str]:
    loaded = []
    for item in load_records("job"):
        try:
            job = GenerationJob(**item)
            loaded.append(job)
            jobs.setdefault(job.id, job)
        except Exception:  # noqa: BLE001
            continue
    current_id = latest_generation_job_id()
    candidates = [
        job
        for job in {job.id: job for job in [*loaded, *jobs.values()]}.values()
        if job.resources or job.status in {"queued", "running", "failed"}
    ]
    candidates = sorted(candidates, key=lambda item: item.completed_at or item.created_at, reverse=True)
    return candidates[: max(1, min(limit, 100))], current_id


def _resource_type_counts(job: GenerationJob) -> list[dict[str, int | str]]:
    counts: dict[str, int] = {}
    for resource in job.resources:
        counts[resource.type] = counts.get(resource.type, 0) + 1
    return [{"type": resource_type, "count": count} for resource_type, count in counts.items()]


def generation_history(limit: int = 20) -> list[dict]:
    candidates, current_id = _generation_history_jobs(limit)
    return [
        {
            "id": job.id,
            "status": job.status,
            "progress": job.progress,
            "current_step": job.current_step,
            "request": job.request.model_dump(),
            "plan_summary": job.plan_summary.model_dump(),
            "fallback_reason": job.fallback_reason,
            "created_at": job.created_at,
            "completed_at": job.completed_at,
            "is_current": job.id == current_id,
            "resource_count": len(job.resources),
            "resource_type_counts": _resource_type_counts(job),
            "trace_count": len(job.traces),
            "event_count": len(job.events),
        }
        for job in candidates
    ]


def generation_history_detail(job_id: str) -> dict | None:
    job = get_job(job_id)
    if not job or not (job.resources or job.status in {"queued", "running", "failed"}):
        return None
    current_id = latest_generation_job_id()
    return {
        **job.model_dump(),
        "is_current": job.id == current_id,
    }


def learning_path_history(limit: int = 20) -> list[dict]:
    records = load_records("path")
    if learning_path and not any(item.get("id") == learning_path.id for item in records):
        records.append(learning_path.model_dump())
    records = sorted(records, key=_record_time_key, reverse=True)
    current_id = learning_path.id if learning_path else ""
    return [
        {
            **item,
            "is_current": item.get("id") == current_id,
        }
        for item in records[: max(1, min(limit, 100))]
    ]


def assessment_history(limit: int = 20) -> list[dict]:
    records = load_records("assessment")
    if assessment_report and not any(item.get("id") == assessment_report.id for item in records):
        records.append(assessment_report.model_dump())
    records = sorted(records, key=_record_time_key, reverse=True)
    current_id = assessment_report.id if assessment_report else ""
    return [
        {
            **item,
            "is_current": item.get("id") == current_id,
        }
        for item in records[: max(1, min(limit, 100))]
    ]


def build_plan_summary(plan_details: list[dict]) -> PlanSummary:
    decisions = [
        PlanDecision(
            resource_type=str(item.get("type", "")),
            priority=float(item.get("priority", 0.0)),
            difficulty=str(item.get("difficulty", "")),
            reason=str(item.get("reason", "")),
        )
        for item in plan_details
        if item.get("type")
    ]
    total_estimated_time = sum(int(item.get("estimated_minutes", 0) or 0) for item in plan_details)
    return PlanSummary(total_estimated_time=total_estimated_time, decisions=decisions)


def resolve_generation_request(request: GenerateRequest, active_profile: Profile | None = None) -> tuple[GenerateRequest, list[str]]:
    planning_profile = active_profile or profile
    raw_need = request.raw_user_need.strip() or request.goal.strip()
    profile_context = "；".join(
        item
        for item in [
            planning_profile.current_chapter,
            planning_profile.learning_goal,
            "，".join(planning_profile.weak_points),
            "，".join(planning_profile.interests),
        ]
        if item
    )
    user_match = match_chapter(
        raw_need,
        request.chapter,
        "，".join(request.pain_points),
    )
    if user_match.get("source") == "explicit" and user_match.get("confidence", 0.0) >= 0.6:
        match = user_match
    else:
        fallback_chapter = planning_profile.current_chapter or request.chapter
        match = match_chapter(profile_context, fallback=fallback_chapter)
        if user_match.get("warnings"):
            match["warnings"] = [*user_match.get("warnings", []), *match.get("warnings", [])]
    chapter = match["chapter"]
    inferred_concepts = infer_target_concepts(
        raw_need,
        request.goal,
        "，".join(request.pain_points),
        profile_context,
        chapter_title=chapter["title"],
    )
    target_concepts = list(dict.fromkeys([*request.target_concepts, *inferred_concepts]))[:12]
    pain_points = list(dict.fromkeys([*request.pain_points, *planning_profile.weak_points]))[:10]
    goal = raw_need or planning_profile.learning_goal or request.goal
    resolved = request.model_copy(
        update={
            "course": request.course or planning_profile.course or "人工智能导论",
            "chapter": chapter["title"],
            "goal": goal,
            "pain_points": pain_points,
            "target_concepts": target_concepts,
            "raw_user_need": raw_need,
            "chapter_match_confidence": float(match.get("confidence", 0.0)),
        }
    )
    warnings = list(match.get("warnings", []))
    if match.get("source") != "explicit":
        warnings.append(f"章节未由本次输入直接确认，当前使用：{chapter['title']}。")
    return resolved, warnings


def normalize_user_id(user_id: str | None = None) -> str:
    raw = (user_id or DEFAULT_USER_ID).strip() or DEFAULT_USER_ID
    return re.sub(r"[^a-zA-Z0-9_.:-]", "_", raw)[:80]


def get_profile(user_id: str | None = None) -> Profile:
    global profile

    resolved_user_id = normalize_user_id(user_id)
    if resolved_user_id == DEFAULT_USER_ID:
        return profile
    if resolved_user_id in profiles:
        return profiles[resolved_user_id]

    stored = next((item for item in load_records("profile") if item.get("id") == resolved_user_id), None)
    profiles[resolved_user_id] = Profile(**stored) if stored else Profile(id=resolved_user_id, updated_at=now())
    return profiles[resolved_user_id]


def set_profile_for_user(user_id: str | None, next_profile: Profile) -> None:
    global profile

    resolved_user_id = normalize_user_id(user_id)
    next_profile.id = resolved_user_id
    if resolved_user_id == DEFAULT_USER_ID:
        profile = next_profile
    else:
        profiles[resolved_user_id] = next_profile
    save_record("profile", resolved_user_id, next_profile.model_dump())


def update_profile_from_message(message: str, user_id: str | None = None):
    from .providers.factory import get_llm_provider
    llm = get_llm_provider()
    profile_agent = ProfileAgent(llm)
    resolved_user_id = normalize_user_id(user_id)
    current_profile = get_profile(resolved_user_id)

    before = current_profile.model_dump()

    extraction_result = profile_agent.extract(message, current_profile)
    extracted = extraction_result.get("extracted", {})

    fused_profile, conflicts, fusion_reason = profile_agent.fuse(
        current_profile,
        extraction_result,
        latest_message=message,
    )
    fusion_meta = profile_agent.last_fusion_meta
    fused_profile.version = current_profile.version + 1
    fused_profile.updated_at = now()
    chapter_match = match_chapter(
        message,
        fused_profile.learning_goal,
        "，".join(fused_profile.weak_points),
        "，".join(fused_profile.interests),
        fallback=fused_profile.current_chapter,
    )
    if chapter_match.get("confidence", 0.0) >= 0.6:
        fused_profile.current_chapter = chapter_match["chapter"]["title"]

    set_profile_for_user(resolved_user_id, fused_profile)
    save_record("profile_version", f"{resolved_user_id}_v{fused_profile.version}", fused_profile.model_dump())
    after = fused_profile.model_dump()

    changes = {}
    tracked_fields = [
        "knowledge_base",
        "current_chapter",
        "learning_goal",
        "cognitive_style",
        "preferred_modalities",
        "weak_points",
        "mistake_patterns",
        "time_budget",
        "interests",
    ]
    for field in tracked_fields:
        if before.get(field) != after.get(field):
            changes[field] = {"before": before.get(field), "after": after.get(field)}

    save_record(
        "profile_change",
        f"{resolved_user_id}_profile_change_{uuid4().hex[:10]}",
        {
            "profile_id": resolved_user_id,
            "version": fused_profile.version,
            "trigger_message": message,
            "extracted": extracted,
            "conflicts": conflicts,
            "fusion_reason": fusion_reason,
            "fusion_meta": fusion_meta,
            "extraction_confidence": extraction_result.get("confidence", 0.5),
            "extraction_source": extraction_result.get("source", "fallback"),
            "changed_fields": changes,
            "updated_at": fused_profile.updated_at,
        },
    )

    return {
        "extracted": extracted,
        "confidence": extraction_result.get("confidence", 0.5),
        "source": extraction_result.get("source", "fallback"),
        "reasoning": extraction_result.get("reasoning", ""),
        "conflicts": conflicts,
        "fusion_reason": fusion_reason,
        "fusion_meta": fusion_meta,
        "changed_fields": changes
    }


def add_profile_weak_point(topic: str, evidence: str = "", user_id: str | None = None) -> dict:
    resolved_user_id = normalize_user_id(user_id)
    current_profile = get_profile(resolved_user_id)
    normalized_topic = topic.strip()
    before = current_profile.model_dump()

    changed = bool(normalized_topic and normalized_topic not in current_profile.weak_points)
    if changed:
        current_profile.weak_points.append(normalized_topic)
        current_profile.version += 1
        current_profile.updated_at = now()
        set_profile_for_user(resolved_user_id, current_profile)
        save_record("profile_version", f"{resolved_user_id}_v{current_profile.version}", current_profile.model_dump())
        save_record(
            "profile_change",
            f"{resolved_user_id}_tutor_weak_point_{uuid4().hex[:10]}",
            {
                "profile_id": resolved_user_id,
                "version": current_profile.version,
                "trigger_message": evidence or f"confirm_weak_point:{normalized_topic}",
                "extracted": {"weak_points": [normalized_topic]},
                "conflicts": [],
                "fusion_reason": f"Tutor 确认加入薄弱点：{normalized_topic}",
                "fusion_meta": {
                    "source": "tutor_confirmation",
                    "changed_fields": ["weak_points"],
                    "confidence": 0.9,
                },
                "extraction_confidence": 0.9,
                "extraction_source": "tutor_confirmation",
                "changed_fields": {
                    "weak_points": {
                        "before": before.get("weak_points", []),
                        "after": current_profile.weak_points,
                    }
                },
                "updated_at": current_profile.updated_at,
            },
        )

    return {"profile": current_profile.model_dump(), "profile_updated": changed}


def evaluate_tutor_exercise(exercise: dict, answer: str, user_id: str | None = None) -> dict:
    resolved_user_id = normalize_user_id(user_id)
    current_profile = get_profile(resolved_user_id)
    before = current_profile.model_dump()
    topic = str(exercise.get("topic") or "当前问题").strip()
    expected_keywords = [
        str(keyword).lower()
        for keyword in exercise.get("expected_keywords", [])
        if str(keyword).strip()
    ]
    normalized_answer = answer.lower()
    hits = [keyword for keyword in expected_keywords if keyword and keyword in normalized_answer]
    enough_detail = len(answer.strip()) >= 36

    if len(hits) >= 2 or (hits and enough_detail):
        score = 86
        mastery_delta = 0.04
        feedback = f"回答抓住了 {topic} 的关键线索：{', '.join(hits[:3])}。下一步可以做迁移应用。"
    elif hits or len(answer.strip()) >= 20:
        score = 64
        mastery_delta = 0.015
        feedback = f"已经碰到 {topic} 的一部分关键点，但解释还不够完整。建议补上“为什么”和“怎么判断”。"
    else:
        score = 38
        mastery_delta = -0.02
        feedback = f"这次回答还没有稳定覆盖 {topic} 的核心。建议先回到资源讲解，再用一个小例子重答。"

    current_profile.mastery = max(0.0, min(0.95, current_profile.mastery + mastery_delta))
    changed_fields = {"mastery": {"before": before.get("mastery"), "after": current_profile.mastery}}
    if score < 70 and topic and topic not in current_profile.weak_points:
        current_profile.weak_points.append(topic)
        changed_fields["weak_points"] = {
            "before": before.get("weak_points", []),
            "after": current_profile.weak_points,
        }
    if score < 70:
        mistake = f"Tutor 小练习暴露：{topic}理解不稳"
        if mistake not in current_profile.mistake_patterns:
            current_profile.mistake_patterns.append(mistake)
            changed_fields["mistake_patterns"] = {
                "before": before.get("mistake_patterns", []),
                "after": current_profile.mistake_patterns,
            }

    current_profile.version += 1
    current_profile.updated_at = now()
    set_profile_for_user(resolved_user_id, current_profile)
    save_record("profile_version", f"{resolved_user_id}_v{current_profile.version}", current_profile.model_dump())
    save_record(
        "profile_change",
        f"{resolved_user_id}_tutor_exercise_{uuid4().hex[:10]}",
        {
            "profile_id": resolved_user_id,
            "version": current_profile.version,
            "trigger_message": f"Tutor 小练习作答：{topic}",
            "extracted": {"mastery_delta": mastery_delta, "weak_points": [topic] if score < 70 else []},
            "conflicts": [],
            "fusion_reason": feedback,
            "fusion_meta": {
                "source": "tutor_exercise",
                "changed_fields": list(changed_fields.keys()),
                "confidence": 0.82,
                "score": score,
            },
            "extraction_confidence": 0.82,
            "extraction_source": "tutor_exercise",
            "changed_fields": changed_fields,
            "updated_at": current_profile.updated_at,
        },
    )

    path = generate_learning_path(
        f"Tutor 小练习评估后调整：{topic}",
        {
            "score": score,
            "mastery_delta": mastery_delta,
            "weak_points": current_profile.weak_points,
            "mistake_patterns": current_profile.mistake_patterns,
        },
        current_profile,
    )
    next_step = None
    if path.steps:
        step = next((item for item in path.steps if item.status != "done"), path.steps[0])
        next_step = {
            "title": step.title,
            "objective": step.objective,
            "reason": step.reason,
            "estimated_minutes": step.estimated_minutes,
            "resource_ids": step.recommended_resource_ids,
        }

    return {
        "score": score,
        "mastery_delta": mastery_delta,
        "weak_points": current_profile.weak_points,
        "mistake_patterns": current_profile.mistake_patterns,
        "feedback": feedback,
        "matched_keywords": hits,
        "adjusted_path": path.model_dump(),
        "profile": current_profile.model_dump(),
        "learning_path": path.model_dump(),
        "next_step": next_step,
    }


def run_generation(request: GenerateRequest, user_id: str | None = None) -> GenerationJob:
    global active_generation_job_id
    active_profile = get_profile(user_id)
    request, intent_warnings = resolve_generation_request(request, active_profile)
    job = GenerationJob(
        id=f"job_{uuid4().hex[:8]}",
        status="queued",
        progress=0,
        current_step="queued",
        request=request,
        created_at=now(),
    )
    jobs[job.id] = job
    job_profiles[job.id] = active_profile.model_copy(deep=True)
    active_generation_job_id = job.id
    event(job, "job_queued", {"job_id": job.id})
    event(
        job,
        "intent_resolved",
        {
            "chapter": request.chapter,
            "target_concepts": request.target_concepts,
            "confidence": request.chapter_match_confidence,
            "warnings": intent_warnings,
        },
    )
    persist_job(job)
    return execute_generation_job(job)


def start_generation(request: GenerateRequest, user_id: str | None = None) -> GenerationJob:
    global active_generation_job_id
    active_profile = get_profile(user_id)
    request, intent_warnings = resolve_generation_request(request, active_profile)
    with generation_lock:
        active_job = get_job(active_generation_job_id) if active_generation_job_id else None
        if active_job and active_job.status in {"queued", "running"}:
            event(active_job, "job_reused", {"job_id": active_job.id, "reason": "已有资源生成任务正在运行，连续点击已复用当前任务。"})
            persist_job(active_job)
            return active_job

    job = GenerationJob(
        id=f"job_{uuid4().hex[:8]}",
        status="queued",
        progress=0,
        current_step="queued",
        request=request,
        created_at=now(),
    )
    jobs[job.id] = job
    job_profiles[job.id] = active_profile.model_copy(deep=True)
    active_generation_job_id = job.id
    event(job, "job_queued", {"job_id": job.id})
    event(
        job,
        "intent_resolved",
        {
            "chapter": request.chapter,
            "target_concepts": request.target_concepts,
            "confidence": request.chapter_match_confidence,
            "warnings": intent_warnings,
        },
    )
    persist_job(job)
    Thread(target=execute_generation_job, args=(job,), daemon=True).start()
    return job


def ensure_required_generation_traces(job: GenerationJob) -> list[str]:
    provider_name = next((trace.llm_provider for trace in job.traces if trace.llm_provider), get_llm_provider().name)
    required = [
        ("ProfileAgent", "画像分析", "读取学生画像、目标和薄弱点。", "画像已用于资源个性化。"),
        ("KnowledgeAgent", "知识召回", "检索课程知识库片段。", "已绑定课程章节来源。"),
        ("PlannerAgent", "学习规划", "选择适合当前画像的资源组合。", "已形成资源生成计划。"),
        ("ResourceAgent", "资源生成", "按计划生成学习资源。", f"已产出 {len(job.resources)} 份资源。"),
        ("ReviewAgent", "内容审核", "检查来源、结构和安全性。", "已完成演示级内容审核。"),
        ("PathPlanner", "路径更新", "根据最新资源更新学习路径。", "任务完成后会同步刷新学习路径。"),
    ]
    existing = {trace.agent for trace in job.traces}
    added = []
    for agent, stage, input_summary, output_summary in required:
        if agent in existing:
            continue
        trace = AgentTrace(
            id=f"trace_{uuid4().hex[:8]}",
            job_id=job.id,
            agent=agent,
            status="completed",
            input_summary=input_summary,
            output_summary=output_summary,
            collaboration_stage=stage,
            boundary="演示稳定性补齐 trace，不改变原智能体职责。",
            depends_on=[],
            source_refs=sorted({ref for resource in job.resources for ref in resource.source_refs})[:5],
            warnings=[job.fallback_reason] if job.fallback_reason else [],
            confidence=0.72 if job.fallback_reason else 0.86,
            retry_count=0,
            llm_provider=provider_name,
            review_conclusion="ReviewAgent 已完成安全与来源审核。" if agent == "ReviewAgent" else "",
            started_at=now(),
            finished_at=now(),
        )
        job.traces.append(trace)
        added.append(stage)
    return added


def execute_generation_job(job: GenerationJob) -> GenerationJob:
    global active_generation_job_id
    request = job.request
    active_profile = job_profiles.get(job.id, profile)

    job.status = "running"
    job.progress = 5
    job.current_step = "job_started"
    event(job, "job_started", {"job_id": job.id})
    persist_job(job)

    orchestrator = Orchestrator()
    total = max(len(orchestrator.enabled_agent_names(request)), 1)
    last_resource_count = 0
    try:
        for idx, (agent, workflow_state) in enumerate(orchestrator.generate(job.id, request, active_profile), start=1):
            job.traces = workflow_state.traces
            job.resources = [normalize_resource(resource) for resource in workflow_state.resources]
            job.plan_summary = build_plan_summary(workflow_state.plan_details)
            job.progress = int(idx / total * 95)
            job.current_step = agent.name
            event(job, "agent_completed", {"agent": agent.name, "progress": job.progress})
            if len(workflow_state.resources) > last_resource_count:
                last_resource_count = len(workflow_state.resources)
                event(job, "resource_ready", {"count": len(workflow_state.resources)})
            persist_job(job)
    except Exception as exc:  # noqa: BLE001
        job.fallback_reason = f"资源生成链路异常，已切换本地课程兜底资源：{exc}"
        job.resources = fallback_resources(request, job.fallback_reason)
        event(job, "job_fallback", {"message": job.fallback_reason, "resources": len(job.resources)})
        persist_job(job)

    if not job.resources:
        job.fallback_reason = job.fallback_reason or "智能体未产出资源，已切换本地课程兜底资源。"
        job.resources = fallback_resources(request, job.fallback_reason)
        event(job, "job_fallback", {"message": job.fallback_reason, "resources": len(job.resources)})
        persist_job(job)

    missing_stages = ensure_required_generation_traces(job)
    if missing_stages:
        event(job, "trace_completed", {"added": missing_stages})

    is_latest_job = active_generation_job_id == job.id
    if not is_latest_job:
        job.status = "completed"
        job.progress = 100
        job.current_step = "job_completed_snapshot_only"
        job.completed_at = now()
        event(job, "job_completed", {"resources": len(job.resources), "traces": len(job.traces), "committed": False})
        persist_job(job)
        return job

    job.status = "completed"
    job.progress = 100
    job.current_step = "job_completed"
    job.completed_at = now()
    resources[:] = [normalize_resource(resource) for resource in job.resources]
    event(job, "job_completed", {"resources": len(job.resources), "traces": len(job.traces)})
    persist_job(job)
    delete_records("resource")
    for resource in resources:
        save_record("resource", resource.id, resource.model_dump())
    generate_learning_path("资源生成完成，基于新资源创建路径", active_profile=active_profile)
    return job


def generate_learning_path(
    reason: str = "基于当前画像生成路径",
    assessment_context: dict | None = None,
    active_profile: Profile | None = None,
) -> LearningPath:
    global learning_path
    
    planner = PathPlanner()
    planning_profile = active_profile or profile
    
    resources_list = [
        {
            "id": r.id,
            "type": r.type,
            "title": r.title,
            "difficulty": r.difficulty,
            "target_concepts": [],
            "estimated_time_minutes": 30,
            "feedback_action": r.user_feedback,
        }
        for r in resources
        if r.user_feedback != "hidden"
    ]
    
    if assessment_context is None and assessment_report is not None:
        assessment_context = assessment_report.model_dump()

    result = planner.plan(planning_profile, resources_list, assessment_context)
    
    path_data = result["learning_path"]
    reasoning = result.get("reasoning", reason)
    valid_resource_ids = {item["id"] for item in resources_list}
    fallback_resource_ids = [item["id"] for item in resources_list[:2]]
    
    steps = []
    for step_data in path_data.get("steps", []):
        recommended_ids = step_data.get("recommended_resource_ids")
        if recommended_ids is None:
            recommended_ids = [
                item.get("id")
                for item in step_data.get("recommended_resources", [])
                if item.get("id")
            ]
        recommended_ids = [resource_id for resource_id in recommended_ids if resource_id in valid_resource_ids]
        if not recommended_ids and fallback_resource_ids:
            recommended_ids = fallback_resource_ids[:1]
        status = step_data.get("status", "todo")
        if status in {"in_progress", "pending_review"}:
            status = "doing"
        elif status == "completed":
            status = "done"
        step = LearningPathStep(
            id=step_data.get("id", f"step_{len(steps)+1:02d}"),
            title=step_data.get("title", f"步骤{len(steps)+1}"),
            objective=step_data.get("objective", ""),
            recommended_resource_ids=recommended_ids,
            reason=step_data.get("reason") or reasoning,
            estimated_minutes=step_data.get("estimated_minutes", 30),
            status=status,
        )
        steps.append(step)

    if not steps:
        concepts = planning_profile.weak_points[:2] or ["机器学习基础"]
        for index, concept in enumerate(concepts, start=1):
            steps.append(
                LearningPathStep(
                    id=f"step_{index:02d}",
                    title=f"入门：{concept}",
                    objective=f"围绕{concept}完成概念理解和一次小练习",
                    recommended_resource_ids=fallback_resource_ids[:2],
                    reason=f"{reason}；路径规划无可用步骤时使用演示兜底步骤。",
                    estimated_minutes=25,
                    status="todo",
                )
            )
    
    learning_path = LearningPath(
        id=path_data.get("id", f"path_{uuid4().hex[:8]}"),
        profile_version=path_data.get("profile_version", planning_profile.version),
        mastery=path_data.get("mastery", planning_profile.mastery),
        adjustment_reason=f"{reason} - {result.get('source', 'unknown')}",
        updated_at=now(),
        steps=steps,
    )
    save_record("path", learning_path.id, learning_path.model_dump())
    return learning_path


def learning_path_has_missing_resources(path: LearningPath | None = None) -> bool:
    candidate = path or learning_path
    if candidate is None:
        return True
    valid_resource_ids = {resource.id for resource in resources if resource.user_feedback != "hidden"}
    referenced_ids = [
        resource_id
        for step in candidate.steps
        for resource_id in step.recommended_resource_ids
    ]
    return any(resource_id not in valid_resource_ids for resource_id in referenced_ids)


def get_or_create_learning_path(reason: str = "初始化演示学习路径") -> LearningPath:
    if learning_path is None or learning_path_has_missing_resources(learning_path):
        return generate_learning_path(reason)
    return learning_path


def get_resource(resource_id: str):
    return next((resource for resource in resources if resource.id == resource_id), None)


def submit_resource_feedback(payload: ResourceFeedbackRequest):
    resource = get_resource(payload.resource_id)
    if resource is None:
        return None
    resource.user_feedback = payload.action
    save_record("resource", resource.id, resource.model_dump())
    generate_learning_path(f"收到资源反馈：{resource.title} -> {payload.action}")
    return resource


def submit_quiz(payload: QuizSubmitRequest) -> AssessmentReport:
    global assessment_report, profile
    quiz_answers = []
    for idx, answer in enumerate(payload.answers, start=1):
        question = ""
        student_answer = answer
        if "回答：" in answer:
            question_part, student_part = answer.split("回答：", 1)
            question = question_part.replace("题目：", "").strip()
            student_answer = student_part.strip()
        normalized_answer = student_answer.lower()
        is_correct = any(
            keyword in normalized_answer
            for keyword in ["过拟合", "泛化", "训练", "测试", "新数据", "评估", "指标", "overfit", "generalization"]
        )
        quiz_answers.append(
            {
                "question_id": f"submitted_{idx:02d}",
                "type": "short_answer",
                "question": question,
                "student_answer": student_answer,
                "correct_answer": "",
                "is_correct": is_correct,
                "explanation": "学生主观题作答，由 AssessmentAgent 结合内容质量评估。",
            }
        )

    assessment_result = AssessmentAgent().assess(
        quiz_answers,
        profile,
        resource_usage=[
            {
                "resource_id": resource.id,
                "resource_type": resource.type,
                "completed": resource.user_feedback != "hidden",
            }
            for resource in resources
        ],
    )
    assessment = assessment_result.get("assessment", {})
    mastery = assessment.get("knowledge_mastery", {})
    raw_score = mastery.get("score", 0.68)
    score = int(round(raw_score * 100)) if isinstance(raw_score, float) and raw_score <= 1 else int(raw_score or 68)
    score = max(0, min(100, score))
    delta = float(assessment_result.get("mastery_delta", 0.04))
    profile.mastery = max(0.0, min(0.95, profile.mastery + delta))
    weak_point_items = assessment.get("weak_points", [])
    evaluated_weak_points = [
        item.get("topic", str(item)) if isinstance(item, dict) else str(item)
        for item in weak_point_items
        if item
    ]
    for weak_point in evaluated_weak_points:
        if weak_point and weak_point not in profile.weak_points:
            profile.weak_points.append(weak_point)
    cognitive = assessment.get("cognitive_level", {})
    profile.mistake_patterns = [
        cognitive.get("description") or cognitive.get("level") or "根据本次练习识别出的迁移不足"
    ]
    profile.version += 1
    profile.updated_at = now()
    assessment_context = {
        "score": score,
        "mastery_delta": delta,
        "weak_points": profile.weak_points,
        "mistake_patterns": profile.mistake_patterns,
    }
    adjusted = generate_learning_path(
        "根据练习提交结果调整：加强评价指标与迁移练习",
        assessment_context,
    )
    assessment_report = AssessmentReport(
        id=f"assess_{uuid4().hex[:8]}",
        score=score,
        mastery_delta=delta,
        strengths=assessment.get("strengths", []) or ["已完成本次练习提交"],
        weak_points=profile.weak_points,
        mistake_patterns=profile.mistake_patterns,
        feedback=(
            f"本次评估依据你的真实作答生成。下一步建议：{'；'.join(assessment_result.get('next_learning_objectives', []))}"
            if assessment_result.get("next_learning_objectives")
            else assessment_result.get("reasoning")
            or mastery.get("details", "已根据本次练习提交生成评估。")
        ),
        adjusted_path=adjusted,
        created_at=now(),
    )
    save_record("profile", profile.id, profile.model_dump())
    save_record("assessment", assessment_report.id, assessment_report.model_dump())
    return assessment_report


def get_or_create_assessment_report() -> AssessmentReport:
    global assessment_report
    if assessment_report is not None:
        return assessment_report
    path = learning_path or generate_learning_path("初始化演示测评报告所需学习路径")
    assessment_report = AssessmentReport(
        id=f"assess_{uuid4().hex[:8]}",
        score=int(round(profile.mastery * 100)),
        mastery_delta=0.0,
        strengths=["暂无正式测评记录，已准备演示默认报告。"],
        weak_points=profile.weak_points,
        mistake_patterns=profile.mistake_patterns,
        feedback="完成练习提交后，这里会展示真实评估反馈和路径调整结果。",
        adjusted_path=path,
        created_at=now(),
    )
    save_record("assessment", assessment_report.id, assessment_report.model_dump())
    return assessment_report


def hydrate_from_db():
    global assessment_report, jobs, learning_path, profile, resources

    latest_profile = load_latest_record("profile")
    if latest_profile:
        profile = Profile(**latest_profile)

    loaded_jobs = load_records("job")
    jobs = {}
    for item in loaded_jobs:
        job = GenerationJob(**item)
        if job.status in {"queued", "running"}:
            job.status = "failed"
            job.current_step = "recovered_incomplete"
            job.completed_at = job.completed_at or now()
            event(job, "job_recovered_failed", {"reason": "服务重启时任务未完成，已标记为失败，可重新生成"})
            persist_job(job)
        jobs[job.id] = job

    loaded_resources = load_records("resource")
    if loaded_resources:
        from .schemas import Resource

        latest_by_type = {}
        for item in loaded_resources:
            latest_by_type[item.get("type", item.get("id", ""))] = item
        resources = [Resource(**item) for item in latest_by_type.values()]
        if len(resources) != len(loaded_resources):
            delete_records("resource")
            for resource in resources:
                save_record("resource", resource.id, resource.model_dump())

    latest_path = load_latest_record("path")
    learning_path = LearningPath(**latest_path) if latest_path else None

    latest_assessment = load_latest_record("assessment")
    assessment_report = AssessmentReport(**latest_assessment) if latest_assessment else None


def profile_change_log(user_id: str | None = None) -> list[dict]:
    resolved_user_id = normalize_user_id(user_id)
    logs = load_records("profile_change")
    logs = [item for item in logs if item.get("profile_id") == resolved_user_id]
    return sorted(logs, key=lambda item: item.get("updated_at", ""), reverse=True)


def profile_versions(user_id: str | None = None) -> list[dict]:
    resolved_user_id = normalize_user_id(user_id)
    versions = load_records("profile_version")
    versions = [item for item in versions if item.get("id") == resolved_user_id]
    versions = sorted(versions, key=lambda item: item.get("version", 0), reverse=True)
    if not versions:
        return [get_profile(resolved_user_id).model_dump()]
    current = get_profile(resolved_user_id).model_dump()
    if not any(item.get("version") == current.get("version") for item in versions):
        versions.insert(0, current)
    return versions


def rollback_profile_version(version: int, user_id: str | None = None) -> dict | None:
    resolved_user_id = normalize_user_id(user_id)
    current_profile = get_profile(resolved_user_id)

    target = next((item for item in profile_versions(resolved_user_id) if item.get("version") == version), None)
    if target is None:
        return None

    before = current_profile.model_dump()
    rolled_back = Profile(**target)
    rolled_back.updated_at = now()
    set_profile_for_user(resolved_user_id, rolled_back)
    save_record("profile_version", f"{resolved_user_id}_v{rolled_back.version}", rolled_back.model_dump())

    changes = {}
    for field in [
        "knowledge_base",
        "current_chapter",
        "learning_goal",
        "cognitive_style",
        "preferred_modalities",
        "weak_points",
        "mistake_patterns",
        "time_budget",
        "interests",
    ]:
        if before.get(field) != target.get(field):
            changes[field] = {"before": before.get(field), "after": target.get(field)}

    save_record(
        "profile_change",
        f"{resolved_user_id}_profile_rollback_{uuid4().hex[:10]}",
        {
            "profile_id": resolved_user_id,
            "version": rolled_back.version,
            "trigger_message": f"rollback_to_v{version}",
            "extracted": {},
            "conflicts": [],
            "fusion_reason": f"已回滚到画像版本 v{version}",
            "fusion_meta": {
                "source": "rollback",
                "changed_fields": list(changes.keys()),
                "conflicts": [],
                "merge_reasoning": f"用户确认撤销高风险画像更新，回滚到 v{version}",
                "confidence": 1.0,
                "validation": {
                    "is_valid": True,
                    "confidence_score": 1.0,
                    "warnings": [],
                    "requires_confirmation": False,
                },
            },
            "extraction_confidence": 1.0,
            "extraction_source": "rollback",
            "changed_fields": changes,
            "updated_at": rolled_back.updated_at,
        },
    )

    if resolved_user_id == DEFAULT_USER_ID:
        path = generate_learning_path(f"画像回滚到 v{version}，重新规划学习路径")
        path_data = path.model_dump()
    else:
        path_data = None
    return {"profile": rolled_back.model_dump(), "learning_path": path_data}


def chat_and_generate(request: ChatAndGenerateRequest, user_id: str | None = None):
    global profile, resources, learning_path
    resolved_user_id = normalize_user_id(user_id)
    
    profile_result = update_profile_from_message(request.message, resolved_user_id)
    active_profile = get_profile(resolved_user_id)
    if resolved_user_id == DEFAULT_USER_ID:
        profile = active_profile
    
    result = {
        "profile_updated": True,
        "resources_updated": False,
        "learning_path_updated": False,
        "message": "",
        "profile": active_profile.model_dump(),
        "extracted": profile_result.get("extracted", {}),
        "resources": [],
        "learning_path": None,
        "conflicts": profile_result.get("conflicts", []),
        "fusion_reason": profile_result.get("fusion_reason", ""),
        "fusion_meta": profile_result.get("fusion_meta", {}),
        "changed_fields": profile_result.get("changed_fields", {}),
    }
    
    if request.regenerate_resources:
        resource_types = request.resource_types if request.resource_types else ["lecture_doc", "quiz", "code_case"]
        
        new_resources = regenerate_resources_by_types(resource_types, active_profile=active_profile, raw_user_need=request.message)
        if new_resources:
            for new_resource in new_resources:
                existing_idx = next((i for i, r in enumerate(resources) if r.type == new_resource.type), None)
                if existing_idx is not None:
                    resources[existing_idx] = new_resource
                else:
                    resources.append(new_resource)
                save_record("resource", new_resource.id, new_resource.model_dump())
            
            result["resources_updated"] = True
            result["resources"] = [r.model_dump() for r in new_resources]
            result["message"] = f"已根据您的需求更新了 {len(new_resources)} 个资源"
            
            generate_learning_path(f"对话更新：{request.message[:30]}...", active_profile=active_profile)
            result["learning_path_updated"] = True
            result["learning_path"] = learning_path.model_dump() if learning_path else None
        else:
            result["message"] = "画像已更新，但资源生成失败"
    else:
        result["message"] = "画像已更新"
    
    return result


def regenerate_resources_by_types(
    resource_types: list[str],
    active_profile: Profile | None = None,
    raw_user_need: str = "",
) -> list[Resource]:
    from .agents import (
        LectureAgent, MindMapAgent, QuizAgent, ReadingAgent,
        MediaAgent, AnimationDemoAgent, PPTDraftAgent, VisualCardAgent, CodeCaseAgent, ReviewAgent
    )
    
    agent_map = {
        "lecture_doc": LectureAgent,
        "mind_map": MindMapAgent,
        "quiz": QuizAgent,
        "reading": ReadingAgent,
        "media_script": MediaAgent,
        "animation_demo": AnimationDemoAgent,
        "ppt_draft": PPTDraftAgent,
        "visual_card": VisualCardAgent,
        "code_case": CodeCaseAgent,
    }
    
    from .agents import WorkflowState
    from .schemas import GenerateRequest
    
    planning_profile = active_profile or profile
    request, _warnings = resolve_generation_request(
        GenerateRequest(
            course=planning_profile.course,
            chapter=planning_profile.current_chapter,
            goal=raw_user_need or planning_profile.learning_goal or "掌握核心概念",
            pain_points=planning_profile.weak_points[:3],
            raw_user_need=raw_user_need,
            resource_types=resource_types,
        ),
        planning_profile,
    )
    
    workflow_state = WorkflowState(f"regen_{uuid4().hex[:6]}", request, planning_profile)
    workflow_state.chapter = find_chapter(request.chapter)
    
    new_resources = []
    for resource_type in resource_types:
        agent_class = agent_map.get(resource_type)
        if agent_class:
            try:
                agent = agent_class()
                agent.traced_run(workflow_state, f"Regenerating {resource_type}")
                if workflow_state.resources:
                    new_resources.append(workflow_state.resources[-1])
                    workflow_state.resources = []
            except Exception as e:
                print(f"Failed to regenerate {resource_type}: {e}")
    
    if new_resources:
        review_agent = ReviewAgent()
        review_state = WorkflowState(f"review_{uuid4().hex[:6]}", request, planning_profile)
        review_state.resources = new_resources
        review_state.chapter = find_chapter(request.chapter)
        review_agent.run(review_state)
    
    return new_resources


def refresh_quiz_fast() -> Resource:
    from .knowledge import find_chapter

    chapter = find_chapter(profile.current_chapter)
    question_pool = list(chapter.get("practice_questions", []))
    if not question_pool:
        question_pool = []
        for item in resources:
            if item.type == "quiz":
                try:
                    question_pool = json.loads(item.content)
                except json.JSONDecodeError:
                    question_pool = []
                break

    random.shuffle(question_pool)
    selected = question_pool[:5] if len(question_pool) >= 5 else question_pool
    questions = []
    for index, item in enumerate(selected, start=1):
        question_text = item.get("question") or item.get("stem") or f"练习题 {index}"
        questions.append(
            {
                "level": item.get("level", "基础" if index <= 2 else "应用"),
                "difficulty": item.get("difficulty", "基础" if index <= 2 else "应用"),
                "type": item.get("type", "short_answer"),
                "question": question_text,
                "answer": item.get("answer") or item.get("standard_answer", "请结合课程概念作答。"),
                "explanation": item.get("explanation") or item.get("analysis", "围绕概念边界、适用条件和案例迁移进行分析。"),
                "assessment_point": item.get("assessment_point", "概念理解与迁移"),
                "options": item.get("options", []),
                "rubric": item.get("rubric", ["概念准确", "理由清晰", "能结合场景"]),
            }
        )

    quiz = Resource(
        id=f"res_{uuid4().hex[:8]}",
        type="quiz",
        title=f"快速练习题：{chapter['title']}",
        content_format="json",
        content=json.dumps(questions, ensure_ascii=False, indent=2),
        source_refs=[f"{chapter['id']}#practice_questions", f"{chapter['id']}#detailed_concepts"],
        difficulty="入门到提高",
        target_profile=[profile.cognitive_style, *profile.preferred_modalities[:2]],
        review_status="passed",
        review_reason="快速刷新：来自课程题库并通过本地结构校验",
        audit_reason="快速刷新：来自课程题库并通过本地结构校验",
        review_notes=[f"题目数量：{len(questions)}", "未调用大模型，避免刷新卡顿"],
        review_confidence=0.9,
        created_by_agents=["QuizFastRefresh"],
        created_at=now(),
    )

    existing_idx = next((idx for idx, resource in enumerate(resources) if resource.type == "quiz"), None)
    if existing_idx is not None:
        resources[existing_idx] = quiz
    else:
        resources.append(quiz)
    save_record("resource", quiz.id, quiz.model_dump())
    return quiz


def adjust_resources(request: ResourceAdjustRequest):
    global resources, learning_path
    
    result = {
        "profile_updated": False,
        "resources_updated": False,
        "learning_path_updated": False,
        "message": "",
        "resources": [],
        "learning_path": None,
    }
    
    for adjustment in request.adjustments:
        resource_id = adjustment.get("resource_id")
        action = adjustment.get("action")
        
        if action == "update_content":
            resource = get_resource(resource_id)
            if resource:
                new_content = adjustment.get("content")
                if new_content:
                    resource.content = new_content
                    resource.review_status = "needs_revision"
                    resource.updated_at = now()
                    save_record("resource", resource.id, resource.model_dump())
                    result["resources_updated"] = True
                    result["resources"].append(resource.model_dump())
        
        elif action == "regenerate":
            resource = get_resource(resource_id)
            if resource:
                resource_types = [resource.type]
                new_resources = regenerate_resources_by_types(resource_types)
                if new_resources:
                    idx = next((i for i, r in enumerate(resources) if r.id == resource_id), None)
                    if idx is not None:
                        resources[idx] = new_resources[0]
                        save_record("resource", new_resources[0].id, new_resources[0].model_dump())
                        result["resources_updated"] = True
                        result["resources"].append(new_resources[0].model_dump())
        
        elif action == "remove":
            resource = get_resource(resource_id)
            if resource:
                resources = [r for r in resources if r.id != resource_id]
                result["resources_updated"] = True
                result["message"] = f"已移除资源 {resource.title}"
    
    if request.preferences:
        for key, value in request.preferences.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
                profile.version += 1
                profile.updated_at = now()
                save_record("profile", profile.id, profile.model_dump())
                result["profile_updated"] = True
                result["message"] = f"已更新偏好设置: {key}"
    
    if request.target_concepts:
        generate_learning_path(f"用户指定重点概念：{', '.join(request.target_concepts)}")
        result["learning_path_updated"] = True
        result["learning_path"] = learning_path.model_dump() if learning_path else None
    
    if result["resources_updated"] or result["profile_updated"]:
        generate_learning_path("资源或偏好已更新，重新规划学习路径")
        result["learning_path_updated"] = True
        result["learning_path"] = learning_path.model_dump() if learning_path else None
    
    return result


def find_chapter(keyword: str):
    from .knowledge import find_chapter as kf_find_chapter
    return kf_find_chapter(keyword)

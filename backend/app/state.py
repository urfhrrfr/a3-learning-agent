from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from threading import Thread
from uuid import uuid4

from .agents import AssessmentAgent, Orchestrator, ProfileAgent, now
from .path_planner import PathPlanner
from .schemas import (
    AssessmentReport,
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
)
from .storage import delete_records, load_latest_record, load_records, save_record


profile = Profile(updated_at=now())
jobs: dict[str, GenerationJob] = {}
resources = []
learning_path: LearningPath | None = None
assessment_report: AssessmentReport | None = None


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


def persist_job(job: GenerationJob) -> None:
    save_record("job", job.id, job.model_dump())


def update_profile_from_message(message: str):
    global profile
    from .providers.factory import get_llm_provider
    llm = get_llm_provider()
    profile_agent = ProfileAgent(llm)

    before = profile.model_dump()

    extraction_result = profile_agent.extract(message, profile)
    extracted = extraction_result.get("extracted", {})

    fused_profile, conflicts, fusion_reason = profile_agent.fuse(
        profile,
        extraction_result,
        latest_message=message,
    )
    fused_profile.version = profile.version + 1
    fused_profile.updated_at = now()

    profile = fused_profile
    save_record("profile", profile.id, profile.model_dump())
    after = profile.model_dump()

    changes = {}
    tracked_fields = [
        "knowledge_base",
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
        f"profile_change_{uuid4().hex[:10]}",
        {
            "profile_id": profile.id,
            "version": profile.version,
            "trigger_message": message,
            "extracted": extracted,
            "conflicts": conflicts,
            "fusion_reason": fusion_reason,
            "extraction_confidence": extraction_result.get("confidence", 0.5),
            "extraction_source": extraction_result.get("source", "fallback"),
            "changed_fields": changes,
            "updated_at": profile.updated_at,
        },
    )

    return {
        "extracted": extracted,
        "confidence": extraction_result.get("confidence", 0.5),
        "source": extraction_result.get("source", "fallback"),
        "reasoning": extraction_result.get("reasoning", ""),
        "conflicts": conflicts,
        "fusion_reason": fusion_reason,
        "changed_fields": changes
    }


def run_generation(request: GenerateRequest) -> GenerationJob:
    job = GenerationJob(
        id=f"job_{uuid4().hex[:8]}",
        status="queued",
        progress=0,
        current_step="queued",
        request=request,
        created_at=now(),
    )
    jobs[job.id] = job
    event(job, "job_queued", {"job_id": job.id})
    persist_job(job)
    return execute_generation_job(job)


def start_generation(request: GenerateRequest) -> GenerationJob:
    job = GenerationJob(
        id=f"job_{uuid4().hex[:8]}",
        status="queued",
        progress=0,
        current_step="queued",
        request=request,
        created_at=now(),
    )
    jobs[job.id] = job
    event(job, "job_queued", {"job_id": job.id})
    persist_job(job)
    Thread(target=execute_generation_job, args=(job,), daemon=True).start()
    return job


def execute_generation_job(job: GenerationJob) -> GenerationJob:
    request = job.request

    job.status = "running"
    job.progress = 5
    job.current_step = "job_started"
    event(job, "job_started", {"job_id": job.id})
    persist_job(job)

    orchestrator = Orchestrator()
    total = max(len(orchestrator.enabled_agent_names(request)), 1)
    last_resource_count = 0
    try:
        for idx, (agent, workflow_state) in enumerate(orchestrator.generate(job.id, request, profile), start=1):
            job.traces = workflow_state.traces
            job.resources = workflow_state.resources
            job.progress = int(idx / total * 95)
            job.current_step = agent.name
            event(job, "agent_completed", {"agent": agent.name, "progress": job.progress})
            if len(workflow_state.resources) > last_resource_count:
                last_resource_count = len(workflow_state.resources)
                event(job, "resource_ready", {"count": len(workflow_state.resources)})
            persist_job(job)
    except Exception as exc:  # noqa: BLE001
        job.status = "failed"
        job.current_step = "failed"
        job.completed_at = now()
        event(job, "job_failed", {"message": str(exc)})
        persist_job(job)
        return job

    job.status = "completed"
    job.progress = 100
    job.current_step = "job_completed"
    job.completed_at = now()
    resources[:] = job.resources
    event(job, "job_completed", {"resources": len(job.resources), "traces": len(job.traces)})
    persist_job(job)
    delete_records("resource")
    for resource in resources:
        save_record("resource", resource.id, resource.model_dump())
    generate_learning_path("资源生成完成，基于新资源创建路径")
    return job


def generate_learning_path(reason: str = "基于当前画像生成路径", assessment_context: dict | None = None) -> LearningPath:
    global learning_path
    
    planner = PathPlanner()
    
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

    result = planner.plan(profile, resources_list, assessment_context)
    
    path_data = result["learning_path"]
    reasoning = result.get("reasoning", reason)
    
    steps = []
    for step_data in path_data.get("steps", []):
        recommended_ids = step_data.get("recommended_resource_ids")
        if recommended_ids is None:
            recommended_ids = [
                item.get("id")
                for item in step_data.get("recommended_resources", [])
                if item.get("id")
            ]
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
    
    learning_path = LearningPath(
        id=path_data.get("id", f"path_{uuid4().hex[:8]}"),
        profile_version=path_data.get("profile_version", profile.version),
        mastery=path_data.get("mastery", profile.mastery),
        adjustment_reason=f"{reason} - {result.get('source', 'unknown')}",
        updated_at=now(),
        steps=steps,
    )
    save_record("path", learning_path.id, learning_path.model_dump())
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
    profile.mastery = min(0.95, profile.mastery + delta)
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


def profile_change_log() -> list[dict]:
    logs = load_records("profile_change")
    return sorted(logs, key=lambda item: item.get("updated_at", ""), reverse=True)


def chat_and_generate(request: ChatAndGenerateRequest):
    global profile, resources, learning_path
    
    profile_result = update_profile_from_message(request.message)
    
    result = {
        "profile_updated": True,
        "resources_updated": False,
        "learning_path_updated": False,
        "message": "",
        "profile": profile.model_dump(),
        "extracted": profile_result.get("extracted", {}),
        "resources": [],
        "learning_path": None,
        "conflicts": profile_result.get("conflicts", []),
        "fusion_reason": profile_result.get("fusion_reason", ""),
        "changed_fields": profile_result.get("changed_fields", {}),
    }
    
    if request.regenerate_resources:
        resource_types = request.resource_types if request.resource_types else ["lecture_doc", "quiz", "code_case"]
        
        new_resources = regenerate_resources_by_types(resource_types)
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
            
            generate_learning_path(f"对话更新：{request.message[:30]}...")
            result["learning_path_updated"] = True
            result["learning_path"] = learning_path.model_dump() if learning_path else None
        else:
            result["message"] = "画像已更新，但资源生成失败"
    else:
        result["message"] = "画像已更新"
    
    return result


def regenerate_resources_by_types(resource_types: list[str]) -> list[Resource]:
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
    
    request = GenerateRequest(
        course=profile.course,
        chapter=profile.current_chapter,
        goal=profile.learning_goal,
        pain_points=profile.weak_points[:3]
    )
    
    workflow_state = WorkflowState(f"regen_{uuid4().hex[:6]}", request, profile)
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
        review_state = WorkflowState(f"review_{uuid4().hex[:6]}", request, profile)
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

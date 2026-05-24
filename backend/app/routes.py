import asyncio
import json
import time

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse

from . import state
from .cache import status as cache_status
from .knowledge import COURSE, find_chapter, question_bank
from .storage import load_records, status as storage_status
from .providers.base import LLMProviderError
from .providers.factory import get_llm_provider
from .retrieval import HybridRetriever, save_retrieval_log
from .schemas import ChatAndGenerateRequest, GenerateRequest, ProfileChatRequest, QuizSubmitRequest, ResourceAdjustRequest, ResourceFeedbackRequest, TutorExerciseSubmitRequest, TutorRequest, WeakPointConfirmRequest
from .path_planner import PathPlanner, LearningProgress
from .vector_store import vector_store_status

router = APIRouter(prefix="/api")


def ok(data):
    return {"ok": True, "data": data, "error": None}


def _detect_tutor_weak_point(question: str, active_profile) -> dict | None:
    text = question.strip().lower()
    confusion_markers = ["不懂", "不会", "没懂", "搞不懂", "不理解", "还是不懂", "看不懂", "困惑", "混淆"]
    if not any(marker in text for marker in confusion_markers):
        return None

    topic_aliases = [
        ("梯度下降", ["梯度下降", "梯度", "gradient descent"]),
        ("反向传播", ["反向传播", "backprop", "back propagation"]),
        ("模型评估指标", ["评估指标", "模型评估", "准确率", "召回率", "f1"]),
        ("过拟合与泛化", ["过拟合", "泛化", "欠拟合"]),
        ("损失函数", ["损失函数", "loss"]),
        ("线性代数", ["线性代数", "线代", "矩阵"]),
    ]
    topic = next((label for label, aliases in topic_aliases if any(alias in text for alias in aliases)), "")
    if not topic:
        return None
    if topic in active_profile.weak_points:
        return {
            "type": "weak_point",
            "topic": topic,
            "confidence": 0.88,
            "already_exists": True,
            "message": f"已识别到你仍在卡住：{topic}，它已经在画像薄弱点中。",
        }
    return {
        "type": "weak_point",
        "topic": topic,
        "confidence": 0.88,
        "already_exists": False,
        "message": f"我识别到“{topic}”可能是新的薄弱点，是否加入画像？",
    }


def _preferred_tutor_mode(active_profile) -> str:
    modalities = active_profile.preferred_modalities or []
    if any(item in modalities for item in ["图解", "动画"]):
        return "图解"
    if any(item in modalities for item in ["代码案例", "代码", "Python"]):
        return "代码"
    if any(item in modalities for item in ["短视频", "视频"]):
        return "短视频脚本"
    if any(item in modalities for item in ["阅读材料", "阅读"]):
        return "例子"
    return active_profile.cognitive_style or "例子"


def _infer_tutor_topic(question: str, profile_suggestion: dict | None, active_profile) -> str:
    if profile_suggestion and profile_suggestion.get("topic"):
        return str(profile_suggestion["topic"])
    text = question.lower()
    for topic, aliases in [
        ("梯度下降", ["梯度下降", "梯度", "gradient descent"]),
        ("反向传播", ["反向传播", "backprop"]),
        ("模型评估指标", ["评估指标", "准确率", "召回率", "f1"]),
        ("过拟合与泛化", ["过拟合", "泛化", "欠拟合"]),
        ("损失函数", ["损失函数", "loss"]),
    ]:
        if any(alias in text for alias in aliases):
            return topic
    return (active_profile.weak_points or ["当前问题"])[0]


def _build_tutor_exercise(topic: str, preferred_mode: str, resource_id: str | None = None) -> dict:
    exercise_map = {
        "梯度下降": {
            "prompt": "用 2-3 句话解释：梯度下降为什么要沿着负梯度方向更新参数？",
            "expected_keywords": ["负梯度", "损失", "下降", "学习率"],
        },
        "反向传播": {
            "prompt": "说明反向传播中链式法则的作用，并举一个两层网络的直观例子。",
            "expected_keywords": ["链式法则", "梯度", "参数", "误差"],
        },
        "模型评估指标": {
            "prompt": "如果一个分类模型准确率很高，但召回率很低，可能意味着什么？",
            "expected_keywords": ["准确率", "召回率", "漏判", "类别不均衡"],
        },
        "过拟合与泛化": {
            "prompt": "训练集表现很好、测试集表现变差时，为什么说模型可能过拟合？",
            "expected_keywords": ["训练集", "测试集", "泛化", "过拟合"],
        },
        "损失函数": {
            "prompt": "损失函数在训练中承担什么角色？它和优化算法是什么关系？",
            "expected_keywords": ["损失", "目标", "优化", "梯度"],
        },
    }
    base = exercise_map.get(
        topic,
        {
            "prompt": f"请用自己的话解释“{topic}”的核心含义，并写出一个你仍不确定的点。",
            "expected_keywords": [topic],
        },
    )
    return {
        "id": f"tutor_ex_{topic}",
        "topic": topic,
        "type": "short_answer",
        "prompt": base["prompt"],
        "expected_keywords": base["expected_keywords"],
        "hint": f"按“{preferred_mode}”方式作答：先写直觉，再写一个检查点。",
        "resource_id": resource_id,
    }


def _build_next_step(active_profile, topic: str) -> dict:
    if state.learning_path and state.learning_path.steps:
        matching_step = next(
            (
                step for step in state.learning_path.steps
                if step.status != "done" and (topic in step.title or topic in step.objective or topic in step.reason)
            ),
            None,
        )
        step = matching_step or next((item for item in state.learning_path.steps if item.status != "done"), state.learning_path.steps[0])
        return {
            "title": step.title,
            "objective": step.objective,
            "reason": step.reason,
            "estimated_minutes": step.estimated_minutes,
            "resource_ids": step.recommended_resource_ids,
        }
    return {
        "title": f"先补齐：{topic}",
        "objective": f"用一个例子和一道小题确认是否理解 {topic}",
        "reason": f"当前画像薄弱点：{'、'.join(active_profile.weak_points[:3]) or topic}",
        "estimated_minutes": 15,
        "resource_ids": [],
    }


def _tutor_profile_context(active_profile, preferred_mode: str) -> str:
    return "\n".join(
        [
            f"学习目标：{active_profile.learning_goal}",
            f"薄弱点：{'、'.join(active_profile.weak_points)}",
            f"易错模式：{'、'.join(active_profile.mistake_patterns)}",
            f"已有基础：{'、'.join(active_profile.knowledge_base)}",
            f"偏好：{preferred_mode}；{'、'.join(active_profile.preferred_modalities)}",
            f"掌握度：{active_profile.mastery:.2f}",
        ]
    )


def _tutor_preferred_sections(preferred_mode: str) -> set[str]:
    sections = {"detailed_concepts", "misconceptions", "difficulties", "practice_questions"}
    if preferred_mode in {"代码", "代码案例"}:
        sections.add("code_labs")
    if preferred_mode in {"图解", "例子"}:
        sections.update({"concept_cards", "real_cases"})
    if preferred_mode in {"短视频脚本", "短视频"}:
        sections.add("real_cases")
    return sections


def _format_rag_sources(sources: list[dict]) -> str:
    if not sources:
        return "暂无课程知识库证据。"
    lines = []
    for source in sources[:5]:
        text = " ".join(str(source.get("text", "")).split())
        if len(text) > 260:
            text = text[:257] + "..."
        lines.append(
            f"- [{source.get('id')}] score={float(source.get('relevance_score', 0)):.2f} "
            f"{source.get('chapter_title', '')}/{source.get('section_label') or source.get('section', '')}：{text}"
        )
    return "\n".join(lines)


def request_user_id(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> str:
    return state.normalize_user_id(x_user_id)


@router.get("/health")
def health():
    provider = get_llm_provider()
    return ok(
        {
            "status": "healthy",
            "mock_llm": provider.name == "mock",
            "llm_provider": provider.name,
            "cache": cache_status(),
            "storage": storage_status(),
            "vector_store": vector_store_status(collection_name=str(COURSE.get("id", "course"))),
            "course": COURSE["title"],
        }
    )


@router.post("/profile/chat")
def profile_chat(payload: ProfileChatRequest, user_id: str = Depends(request_user_id)):
    update_result = state.update_profile_from_message(payload.message, user_id)
    current_profile = state.get_profile(user_id)
    suggested_questions = [
        "你希望下一份资源更偏图解、代码实操，还是练习巩固？",
        "你对哪个部分的学习感到最困难？",
        "你平常每天有多少时间可以投入学习？",
        "除了这门课，你还对什么方向感兴趣？"
    ]
    return ok(
        {
            "profile": current_profile.model_dump(),
            "extracted": update_result.get("extracted", {}),
            "confidence": update_result.get("confidence", 0.5),
            "source": update_result.get("source", "fallback"),
            "reasoning": update_result.get("reasoning", ""),
            "conflicts": update_result.get("conflicts", []),
            "fusion_reason": update_result.get("fusion_reason", ""),
            "fusion_meta": update_result.get("fusion_meta", {}),
            "changed_fields": update_result.get("changed_fields", {}),
            "suggested_next_question": suggested_questions[0],
            "suggested_next_questions": suggested_questions,
            "version_change": f"画像已更新到 v{current_profile.version}",
        }
    )


@router.get("/profile/current")
def profile_current(user_id: str = Depends(request_user_id)):
    return ok(state.get_profile(user_id).model_dump())


@router.get("/profile/versions")
def profile_versions(user_id: str = Depends(request_user_id)):
    return ok(state.profile_versions(user_id))


@router.post("/profile/rollback/{version}")
def profile_rollback(version: int, user_id: str = Depends(request_user_id)):
    result = state.rollback_profile_version(version, user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="profile version not found")
    return ok(result)


@router.get("/profile/dimensions")
def profile_dimensions():
    return ok(state.PROFILE_DIMENSIONS)


@router.get("/profile/change-log")
def profile_change_log(user_id: str = Depends(request_user_id)):
    return ok(state.profile_change_log(user_id))


@router.post("/profile/chat-and-generate")
def profile_chat_and_generate(payload: ChatAndGenerateRequest, user_id: str = Depends(request_user_id)):
    result = state.chat_and_generate(payload, user_id)
    return ok(result)


@router.post("/profile/weak-points/confirm")
def profile_confirm_weak_point(payload: WeakPointConfirmRequest, user_id: str = Depends(request_user_id)):
    return ok(state.add_profile_weak_point(payload.topic, payload.evidence, user_id))


@router.post("/resources/adjust")
def resources_adjust(payload: ResourceAdjustRequest):
    result = state.adjust_resources(payload)
    return ok(result)


@router.post("/resources/generate")
def resources_generate(payload: GenerateRequest, user_id: str = Depends(request_user_id)):
    job = state.run_generation(payload, user_id)
    return ok(job.model_dump())


@router.post("/resources/generate/background")
def resources_generate_background(payload: GenerateRequest, user_id: str = Depends(request_user_id)):
    job = state.start_generation(payload, user_id)
    return ok(job.model_dump())


@router.post("/resources/generate/stream")
def resources_generate_stream(payload: GenerateRequest, user_id: str = Depends(request_user_id)):
    job = state.start_generation(payload, user_id)
    
    def generate():
        last_progress = 0
        last_resource_count = 0
        
        while job.status not in {"completed", "failed"}:
            if job.progress > last_progress:
                last_progress = job.progress
                yield json.dumps({
                    "type": "progress",
                    "progress": job.progress,
                    "current_step": job.current_step,
                    "status": job.status,
                }, ensure_ascii=False) + "\n"
            
            if len(job.resources) > last_resource_count:
                new_resources = job.resources[last_resource_count:]
                last_resource_count = len(job.resources)
                for resource in new_resources:
                    yield json.dumps({
                        "type": "resource_ready",
                        "resource": resource.model_dump(),
                    }, ensure_ascii=False) + "\n"
            
            time.sleep(0.3)
        
        if job.status == "completed":
            yield json.dumps({
                "type": "completed",
                "progress": 100,
                "resource_count": len(job.resources),
                "job_id": job.id,
            }, ensure_ascii=False) + "\n"
        else:
            yield json.dumps({
                "type": "failed",
                "error": job.events[-1]["payload"]["message"] if job.events else "Unknown error",
            }, ensure_ascii=False) + "\n"
    
    return StreamingResponse(generate(), media_type="application/jsonlines; charset=utf-8")


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = state.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return ok(job.model_dump())


@router.get("/jobs/{job_id}/events")
async def job_events(job_id: str):
    job = state.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    async def generate():
        index = 0
        timeout_count = 0
        while True:
            while index < len(job.events):
                item = job.events[index]
                index += 1
                yield f"event: {item['type']}\ndata: {json.dumps(item, ensure_ascii=False)}\n\n"
                timeout_count = 0
            if job.status in {"completed", "failed"}:
                yield f"event: {job.status}\ndata: {json.dumps({'job_id': job_id, 'status': job.status, 'fallback_reason': job.fallback_reason}, ensure_ascii=False)}\n\n"
                break
            await asyncio.sleep(0.2)
            timeout_count += 1
            if timeout_count > 300:
                break

    headers = {
        'Content-Type': 'text/event-stream; charset=utf-8',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Cache-Control',
    }
    return StreamingResponse(generate(), headers=headers, media_type="text/event-stream")


@router.get("/resources")
def list_resources():
    return ok([state.normalize_resource(resource).model_dump() for resource in state.resources])


@router.get("/resources/history")
def resources_history(limit: int = 20):
    return ok(state.generation_history(limit))


@router.get("/resources/history/{job_id}")
def resources_history_detail(job_id: str):
    job = state.generation_history_detail(job_id)
    if job:
        return ok(job)
    raise HTTPException(status_code=404, detail="history job not found")


@router.get("/resources/{resource_id}")
def get_resource(resource_id: str):
    resource = state.get_resource(resource_id)
    if resource:
        return ok(state.normalize_resource(resource).model_dump())
    raise HTTPException(status_code=404, detail="resource not found")


@router.post("/resources/feedback")
def resource_feedback(payload: ResourceFeedbackRequest):
    resource = state.submit_resource_feedback(payload)
    if resource:
        return ok({"resource": resource.model_dump(), "learning_path": state.learning_path.model_dump() if state.learning_path else None})
    raise HTTPException(status_code=404, detail="resource not found")


@router.post("/learning-path/generate")
def learning_path_generate():
    return ok(state.generate_learning_path().model_dump())


@router.get("/learning-path/current")
def learning_path_current():
    path = state.get_or_create_learning_path("初始化或修复演示学习路径")
    return ok(path.model_dump())


@router.get("/learning-path/history")
def learning_path_history(limit: int = 20):
    return ok(state.learning_path_history(limit))


@router.post("/learning-path/feedback")
def learning_path_feedback():
    return ok(state.generate_learning_path("收到反馈后缩短概念复习、增加代码迁移").model_dump())


@router.post("/learning-path/adjust")
def learning_path_adjust():
    planner = PathPlanner()
    
    current_path = state.learning_path.model_dump() if state.learning_path else {}
    if not current_path:
        current_path = {
            "id": "path_default",
            "profile_version": 1,
            "mastery": state.profile.mastery,
            "overall_goal": state.profile.learning_goal,
            "adjustment_reason": "",
            "steps": []
        }
    
    assessment = {}
    if state.assessment_report:
        assessment = {
            "mastery_delta": 0.05,
            "assessment": {
                "weak_points": [{"topic": wp, "severity": "high"} for wp in state.profile.weak_points[:2]]
            }
        }
    
    result = planner.adjust(current_path, assessment, state.profile)
    return ok(result)


@router.post("/learning-path/prioritize")
def learning_path_prioritize():
    planner = PathPlanner()
    
    resources = []
    for resource in state.resources:
        resources.append({
            "id": resource.id,
            "type": resource.type,
            "title": resource.title,
            "difficulty": "基础",
            "estimated_time_minutes": 20
        })
    
    assessment = {}
    if state.assessment_report:
        assessment = {
            "mastery_delta": 0.05,
            "assessment": {
                "knowledge_mastery": {"level": "良好"},
                "weak_points": [{"topic": wp} for wp in state.profile.weak_points[:2]]
            }
        }
    
    result = planner.prioritize_resources(state.profile, assessment, resources)
    return ok(result)


@router.get("/learning-path/progress")
def learning_path_progress():
    path = state.get_or_create_learning_path("初始化或修复演示学习路径")
    
    progress = LearningProgress(path.id)
    progress.completed_steps = ["step_01"]
    progress.total_time_spent_minutes = 45
    progress.record_quiz_score("quiz_01", 0.75, 10)
    
    planner = PathPlanner()
    summary = planner.generate_progress_summary(path.model_dump(), progress)
    return ok(summary)


@router.post("/learning-path/progress/update")
def update_learning_progress(step_id: str = None, resource_id: str = None, completed: bool = False):
    if state.learning_path is None:
        return ok({"message": "No learning path found"})
    
    progress = LearningProgress(state.learning_path.id)
    
    if step_id:
        progress.mark_step_completed(step_id)
    
    if resource_id:
        progress.record_resource_usage(resource_id, 20, completed)
    
    planner = PathPlanner()
    summary = planner.generate_progress_summary(state.learning_path.model_dump(), progress)
    return ok(summary)


@router.post("/tutor/chat")
def tutor_chat(payload: TutorRequest, user_id: str = Depends(request_user_id)):
    active_profile = state.get_profile(user_id)
    profile_suggestion = _detect_tutor_weak_point(payload.question, active_profile)
    preferred_mode = _preferred_tutor_mode(active_profile)
    tutor_topic = _infer_tutor_topic(payload.question, profile_suggestion, active_profile)
    current_chapter = find_chapter(active_profile.current_chapter or tutor_topic or "机器学习基础")
    provider = get_llm_provider()
    rag_profile_context = _tutor_profile_context(active_profile, preferred_mode)
    rag_sources, rag_warnings = HybridRetriever(COURSE, llm=provider, max_candidates=12, top_k=5).retrieve(
        query=f"{payload.question}；当前主题：{tutor_topic}",
        profile_context=rag_profile_context,
        current_chapter_id=current_chapter["id"],
        preferred_sections=_tutor_preferred_sections(preferred_mode),
    )
    save_retrieval_log(
        scenario="tutor_chat",
        user_id=user_id,
        query=payload.question,
        profile_snapshot=active_profile.model_dump(),
        selected_sources=rag_sources,
        request_context={
            "topic": tutor_topic,
            "preferred_mode": preferred_mode,
            "current_chapter_id": current_chapter["id"],
            "resource_id": payload.resource_id,
        },
        warnings=rag_warnings,
    )
    rag_context = _format_rag_sources(rag_sources)
    selected_resource = state.get_resource(payload.resource_id) if payload.resource_id else None
    context_resources = [selected_resource] if selected_resource else state.resources[:3]
    cited_resources = [
        {
            "id": resource.id,
            "title": resource.title,
            "type": resource.type,
            "difficulty": resource.difficulty,
        }
        for resource in context_resources
        if resource
    ]
    resource_context = "\n\n".join(
        (
            f"资源标题：{resource.title}\n"
            f"资源类型：{resource.type}\n"
            f"引用来源：{resource.source_refs}\n"
            f"内容片段：{resource.content[:500]}"
        )
        for resource in context_resources
        if resource
    )
    resource_refs = {ref for resource in context_resources if resource for ref in resource.source_refs}
    rag_refs = {str(source.get("id")) for source in rag_sources if source.get("id")}
    source_refs = sorted(rag_refs | resource_refs) or ["ai_intro/ch04#concepts"]
    history_items = []
    for item in payload.history[-8:]:
        role = item.get("role", "")
        content = item.get("content", "").strip()
        if role in {"user", "assistant"} and content:
            label = "学生" if role == "user" else "导师"
            history_items.append(f"{label}: {content[:600]}")
    history_context = "\n".join(history_items) or "暂无历史对话。"
    fallback_answer = (
        f"我会按你当前偏好的“{preferred_mode}”方式来讲。"
        "可以先把问题拆成“直觉、步骤、检查点”三层：先看它想解决什么，再看每一步怎么算，最后用一个小例子判断自己是否真的会用。"
    )
    if rag_sources:
        fallback_answer = (
            f"我会按你当前偏好的“{preferred_mode}”方式来讲。"
            f"课程知识库里最相关的是 [{rag_sources[0]['id']}]：{str(rag_sources[0].get('text', ''))[:180]}。"
            "你可以先抓住它对应的概念边界，再用一个小例子检查自己是否会迁移。"
        )
    answer = fallback_answer
    fallback_reason = ""
    if provider.name != "mock":
        try:
            answer = provider.complete(
                "你是一个高校课程智能辅导大模型，不是固定 FAQ。请根据学生问题动态回答。\n"
                "回答要求：\n"
                "1. 使用中文，语气像耐心助教，先直接回应问题，再分步骤解释。\n"
                "2. 必须结合学生画像、课程知识库 RAG 证据和已生成课程资源，不要脱离上下文泛泛而谈。\n"
                "3. 如果学生问题很短，也要先判断其可能困惑点，再给一个例子和一个追问。\n"
                "4. 不要每次套用同一段话；同一主题也要根据问题措辞调整解释角度。\n"
                "5. 参考最近对话，保持连续性；不要把已解释过的内容原样重复一遍。\n"
                "6. 末尾给出“你可以继续问我：...”的一句具体追问建议。\n\n"
                "7. 必须按学生 preferred_modalities 调整表达：图解偏好就用文字图示/流程图；代码偏好就给最小 Python 片段；短视频偏好就给 3 镜头脚本；例子偏好就用生活类比和反例。\n"
                "8. 如果识别到画像更新建议，只在回答里温和提示，不要声称已经更新画像。\n\n"
                f"学生画像：{active_profile.model_dump()}\n\n"
                f"本次推荐讲解方式：{preferred_mode}\n"
                f"画像更新建议：{profile_suggestion or '无'}\n\n"
                f"课程知识库 RAG 证据：\n{rag_context}\n\n"
                f"当前已生成资源上下文：\n{resource_context or '暂无已生成资源，请优先基于 RAG 证据、学生画像和问题回答。'}\n\n"
                f"最近对话历史：\n{history_context}\n\n"
                f"学生问题：{payload.question}\n"
            ).strip() or fallback_answer
        except (LLMProviderError, Exception) as exc:
            fallback_reason = str(exc)
            answer = fallback_answer
    elif provider.name == "mock":
        fallback_reason = "当前是 mock provider"
    return ok(
        {
            "answer": answer,
            "source_refs": source_refs,
            "mermaid": "",
            "llm_provider": provider.name,
            "used_fallback": answer == fallback_answer,
            "fallback_reason": fallback_reason,
            "retrieval_warnings": rag_warnings,
            "profile_suggestion": profile_suggestion,
            "profile_snapshot": active_profile.model_dump(),
            "personalization": {
                "preferred_mode": preferred_mode,
                "preferred_modalities": active_profile.preferred_modalities,
                "weak_points": active_profile.weak_points,
            },
            "cited_resources": cited_resources,
            "evidence_sources": rag_sources,
            "next_step": _build_next_step(active_profile, tutor_topic),
            "exercise": _build_tutor_exercise(tutor_topic, preferred_mode, selected_resource.id if selected_resource else None),
        }
    )


@router.post("/tutor/exercise/submit")
def tutor_exercise_submit(payload: TutorExerciseSubmitRequest, user_id: str = Depends(request_user_id)):
    return ok(state.evaluate_tutor_exercise(payload.exercise, payload.answer, user_id))


@router.post("/quiz/submit")
def quiz_submit(payload: QuizSubmitRequest):
    return ok(state.submit_quiz(payload).model_dump())


@router.post("/quiz/refresh")
def quiz_refresh():
    quiz = state.refresh_quiz_fast()
    return ok(quiz.model_dump())


@router.get("/assessment/report")
def assessment_report():
    return ok(state.get_or_create_assessment_report().model_dump())


@router.get("/assessment/history")
def assessment_history(limit: int = 20):
    return ok(state.assessment_history(limit))


@router.get("/course/chunks")
def course_chunks():
    return ok({"course": COURSE, "question_count": len(question_bank()), "questions": question_bank()})


@router.get("/retrieval/logs")
def retrieval_logs(limit: int = 20):
    logs = sorted(load_records("retrieval_log"), key=lambda item: item.get("created_at", ""), reverse=True)
    return ok(logs[: max(1, min(limit, 100))])

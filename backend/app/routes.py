import asyncio
import json
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from . import state
from .knowledge import COURSE, question_bank
from .providers.base import LLMProviderError
from .providers.factory import get_llm_provider
from .schemas import ChatAndGenerateRequest, GenerateRequest, ProfileChatRequest, QuizSubmitRequest, ResourceAdjustRequest, ResourceFeedbackRequest, TutorRequest
from .path_planner import PathPlanner, LearningProgress

router = APIRouter(prefix="/api")


def ok(data):
    return {"ok": True, "data": data, "error": None}


@router.get("/health")
def health():
    provider = get_llm_provider()
    return ok({"status": "healthy", "mock_llm": provider.name == "mock", "llm_provider": provider.name, "course": COURSE["title"]})


@router.post("/profile/chat")
def profile_chat(payload: ProfileChatRequest):
    update_result = state.update_profile_from_message(payload.message)
    suggested_questions = [
        "你希望下一份资源更偏图解、代码实操，还是练习巩固？",
        "你对哪个部分的学习感到最困难？",
        "你平常每天有多少时间可以投入学习？",
        "除了这门课，你还对什么方向感兴趣？"
    ]
    return ok(
        {
            "profile": state.profile.model_dump(),
            "extracted": update_result.get("extracted", {}),
            "confidence": update_result.get("confidence", 0.5),
            "source": update_result.get("source", "fallback"),
            "reasoning": update_result.get("reasoning", ""),
            "conflicts": update_result.get("conflicts", []),
            "fusion_reason": update_result.get("fusion_reason", ""),
            "changed_fields": update_result.get("changed_fields", {}),
            "suggested_next_question": suggested_questions[0],
            "suggested_next_questions": suggested_questions,
            "version_change": f"画像已更新到 v{state.profile.version}",
        }
    )


@router.get("/profile/current")
def profile_current():
    return ok(state.profile.model_dump())


@router.get("/profile/versions")
def profile_versions():
    return ok([state.profile.model_dump()])


@router.get("/profile/dimensions")
def profile_dimensions():
    return ok(state.PROFILE_DIMENSIONS)


@router.get("/profile/change-log")
def profile_change_log():
    return ok(state.profile_change_log())


@router.post("/profile/chat-and-generate")
def profile_chat_and_generate(payload: ChatAndGenerateRequest):
    result = state.chat_and_generate(payload)
    return ok(result)


@router.post("/resources/adjust")
def resources_adjust(payload: ResourceAdjustRequest):
    result = state.adjust_resources(payload)
    return ok(result)


@router.post("/resources/generate")
def resources_generate(payload: GenerateRequest):
    job = state.run_generation(payload)
    return ok(job.model_dump())


@router.post("/resources/generate/background")
def resources_generate_background(payload: GenerateRequest):
    job = state.start_generation(payload)
    return ok(job.model_dump())


@router.post("/resources/generate/stream")
def resources_generate_stream(payload: GenerateRequest):
    job = state.start_generation(payload)
    
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
    
    return StreamingResponse(generate(), media_type="application/jsonlines")


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = state.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return ok(job.model_dump())


@router.get("/jobs/{job_id}/events")
async def job_events(job_id: str):
    job = state.jobs.get(job_id)
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
                yield f"event: completed\ndata: {json.dumps({'job_id': job_id, 'status': job.status})}\n\n"
                break
            await asyncio.sleep(0.2)
            timeout_count += 1
            if timeout_count > 300:
                break

    headers = {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Cache-Control',
    }
    return StreamingResponse(generate(), headers=headers, media_type="text/event-stream")


@router.get("/resources")
def list_resources():
    return ok([resource.model_dump() for resource in state.resources])


@router.get("/resources/{resource_id}")
def get_resource(resource_id: str):
    resource = state.get_resource(resource_id)
    if resource:
        return ok(resource.model_dump())
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
    if state.learning_path is None:
        state.generate_learning_path("初始化演示学习路径")
    return ok(state.learning_path.model_dump())


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
    if state.learning_path is None:
        state.generate_learning_path("初始化演示学习路径")
    
    progress = LearningProgress(state.learning_path.id)
    progress.completed_steps = ["step_01"]
    progress.total_time_spent_minutes = 45
    progress.record_quiz_score("quiz_01", 0.75, 10)
    
    planner = PathPlanner()
    summary = planner.generate_progress_summary(state.learning_path.model_dump(), progress)
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
def tutor_chat(payload: TutorRequest):
    selected_resource = state.get_resource(payload.resource_id) if payload.resource_id else None
    context_resources = [selected_resource] if selected_resource else state.resources[:3]
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
    source_refs = sorted({ref for resource in context_resources if resource for ref in resource.source_refs}) or ["ai_intro/ch04#concepts"]
    fallback_answer = (
        "可以把当前问题拆成“概念定义、适用条件、反例”三步。"
        "结合你的画像，我会先给例子再给公式：训练集像课堂练习，测试集像新试卷，泛化能力就是新试卷上的表现。"
    )
    provider = get_llm_provider()
    answer = fallback_answer
    fallback_reason = ""
    if provider.name != "mock":
        try:
            answer = provider.complete(
                "你是一个高校课程智能辅导大模型，不是固定 FAQ。请根据学生问题动态回答。\n"
                "回答要求：\n"
                "1. 使用中文，语气像耐心助教，先直接回应问题，再分步骤解释。\n"
                "2. 必须结合学生画像和已生成课程资源，不要脱离上下文泛泛而谈。\n"
                "3. 如果学生问题很短，也要先判断其可能困惑点，再给一个例子和一个追问。\n"
                "4. 不要每次套用同一段话；同一主题也要根据问题措辞调整解释角度。\n"
                "5. 末尾给出“你可以继续问我：...”的一句具体追问建议。\n\n"
                f"学生画像：{state.profile.model_dump()}\n\n"
                f"当前课程资源上下文：\n{resource_context or '暂无已生成资源，请基于课程画像和问题回答。'}\n\n"
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
        }
    )


@router.post("/quiz/submit")
def quiz_submit(payload: QuizSubmitRequest):
    return ok(state.submit_quiz(payload).model_dump())


@router.post("/quiz/refresh")
def quiz_refresh():
    quiz = state.refresh_quiz_fast()
    return ok(quiz.model_dump())


@router.get("/assessment/report")
def assessment_report():
    if state.assessment_report is None:
        return ok(None)
    return ok(state.assessment_report.model_dump())


@router.get("/course/chunks")
def course_chunks():
    return ok({"course": COURSE, "question_count": len(question_bank()), "questions": question_bank()})

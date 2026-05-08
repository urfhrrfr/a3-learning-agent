import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from . import state
from .knowledge import COURSE, question_bank
from .schemas import GenerateRequest, ProfileChatRequest, QuizSubmitRequest, TutorRequest

router = APIRouter(prefix="/api")


def ok(data):
    return {"ok": True, "data": data, "error": None}


@router.get("/health")
def health():
    return ok({"status": "healthy", "mock_llm": True, "course": COURSE["title"]})


@router.post("/profile/chat")
def profile_chat(payload: ProfileChatRequest):
    extracted = state.update_profile_from_message(payload.message)
    return ok(
        {
            "profile": state.profile.model_dump(),
            "extracted": extracted,
            "suggested_next_question": "你希望下一份资源更偏图解、代码实操，还是练习巩固？",
            "version_change": f"画像已更新到 v{state.profile.version}",
        }
    )


@router.get("/profile/current")
def profile_current():
    return ok(state.profile.model_dump())


@router.get("/profile/versions")
def profile_versions():
    return ok([state.profile.model_dump()])


@router.post("/resources/generate")
def resources_generate(payload: GenerateRequest):
    job = state.run_generation(payload)
    return ok(job.model_dump())


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = state.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return ok(job.model_dump())


@router.get("/jobs/{job_id}/events")
def job_events(job_id: str):
    job = state.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    def generate():
        for item in job.events:
            yield f"event: {item['type']}\ndata: {json.dumps(item, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/resources")
def list_resources():
    return ok([resource.model_dump() for resource in state.resources])


@router.get("/resources/{resource_id}")
def get_resource(resource_id: str):
    for resource in state.resources:
        if resource.id == resource_id:
            return ok(resource.model_dump())
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


@router.post("/tutor/chat")
def tutor_chat(payload: TutorRequest):
    answer = (
        "可以把当前问题拆成“概念定义、适用条件、反例”三步。"
        "结合你的画像，我会先给例子再给公式：训练集像课堂练习，测试集像新试卷，泛化能力就是新试卷上的表现。"
    )
    return ok(
        {
            "answer": answer,
            "source_refs": ["ai_intro/ch04#concepts"],
            "mermaid": "flowchart LR\nA[训练数据] --> B[模型]\nB --> C[预测]\nC --> D[评价指标]",
        }
    )


@router.post("/quiz/submit")
def quiz_submit(payload: QuizSubmitRequest):
    return ok(state.submit_quiz(payload).model_dump())


@router.get("/assessment/report")
def assessment_report():
    if state.assessment_report is None:
        return ok(None)
    return ok(state.assessment_report.model_dump())


@router.get("/course/chunks")
def course_chunks():
    return ok({"course": COURSE, "question_count": len(question_bank()), "questions": question_bank()})

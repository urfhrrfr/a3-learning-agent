from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .agents import Orchestrator, now
from .schemas import (
    AssessmentReport,
    GenerateRequest,
    GenerationJob,
    LearningPath,
    LearningPathStep,
    Profile,
    QuizSubmitRequest,
)
from .storage import load_records, save_record


profile = Profile(updated_at=now())
jobs: dict[str, GenerationJob] = {}
resources = []
learning_path: LearningPath | None = None
assessment_report: AssessmentReport | None = None


def event(job: GenerationJob, event_type: str, payload: dict):
    item = {"type": event_type, "payload": payload, "created_at": now()}
    job.events.append(item)
    return item


def update_profile_from_message(message: str):
    global profile
    extracted = {}
    if "数学" in message or "线代" in message or "线性代数" in message:
        if "线性代数薄弱" not in profile.knowledge_base:
            profile.knowledge_base.append("线性代数薄弱")
        extracted["weak_math"] = True
    if "代码" in message or "Python" in message:
        if "代码案例" not in profile.preferred_modalities:
            profile.preferred_modalities.append("代码案例")
        extracted["preferred_modality"] = "代码案例"
    if "考研" in message or "项目" in message:
        profile.learning_goal = "面向课程项目和考试掌握人工智能核心方法"
        extracted["learning_goal"] = profile.learning_goal
    if "视频" in message or "动画" in message:
        if "短视频" not in profile.preferred_modalities:
            profile.preferred_modalities.append("短视频")
        extracted["preferred_modality"] = "短视频"
    if "梯度" in message:
        if "梯度下降" not in profile.weak_points:
            profile.weak_points.append("梯度下降")
        extracted["weak_point"] = "梯度下降"
    profile.version += 1
    profile.updated_at = now()
    save_record("profile", profile.id, profile.model_dump())
    return extracted


def run_generation(request: GenerateRequest) -> GenerationJob:
    job = GenerationJob(
        id=f"job_{uuid4().hex[:8]}",
        status="running",
        progress=5,
        current_step="job_started",
        request=request,
        created_at=now(),
    )
    jobs[job.id] = job
    event(job, "job_started", {"job_id": job.id})
    orchestrator = Orchestrator()
    total = len(orchestrator.agents)
    for idx, (agent, state) in enumerate(orchestrator.generate(job.id, request, profile), start=1):
        job.traces = state.traces
        job.resources = state.resources
        job.progress = int(idx / total * 95)
        job.current_step = agent.name
        event(job, "agent_completed", {"agent": agent.name, "progress": job.progress})
        if state.resources:
            event(job, "resource_ready", {"count": len(state.resources)})
    job.status = "completed"
    job.progress = 100
    job.current_step = "job_completed"
    job.completed_at = now()
    resources[:] = job.resources
    event(job, "job_completed", {"resources": len(job.resources), "traces": len(job.traces)})
    save_record("job", job.id, job.model_dump())
    for resource in resources:
        save_record("resource", resource.id, resource.model_dump())
    generate_learning_path("资源生成完成，基于新资源创建路径")
    return job


def generate_learning_path(reason: str = "基于当前画像生成路径") -> LearningPath:
    global learning_path
    res_ids = [resource.id for resource in resources]
    learning_path = LearningPath(
        id=f"path_{uuid4().hex[:8]}",
        profile_version=profile.version,
        mastery=profile.mastery,
        adjustment_reason=reason,
        updated_at=now(),
        steps=[
            LearningPathStep(
                id="step_01",
                title="概念热身",
                objective="建立章节框架，识别易混概念",
                recommended_resource_ids=res_ids[:2],
                reason="画像显示偏好图解和例子驱动，先用讲解与导图降低门槛。",
                estimated_minutes=20,
                status="doing",
            ),
            LearningPathStep(
                id="step_02",
                title="分层练习",
                objective="用题目暴露薄弱点",
                recommended_resource_ids=res_ids[2:3],
                reason="当前掌握度偏低，需要通过基础到提高题定位误区。",
                estimated_minutes=25,
            ),
            LearningPathStep(
                id="step_03",
                title="代码迁移",
                objective="把概念转成可运行小实验",
                recommended_resource_ids=res_ids[3:],
                reason="学生偏好代码案例，使用脚本和实操案例巩固。",
                estimated_minutes=40,
            ),
        ],
    )
    save_record("path", learning_path.id, learning_path.model_dump())
    return learning_path


def submit_quiz(payload: QuizSubmitRequest) -> AssessmentReport:
    global assessment_report, profile
    joined = " ".join(payload.answers)
    score = 86 if "过拟合" in joined or "泛化" in joined else 68
    delta = 0.12 if score >= 80 else 0.04
    profile.mastery = min(0.95, profile.mastery + delta)
    if score < 80 and "评价指标混淆" not in profile.weak_points:
        profile.weak_points.append("评价指标混淆")
    profile.mistake_patterns = ["概念能说出但迁移不足"] if score < 80 else ["少量术语表达不严谨"]
    profile.version += 1
    profile.updated_at = now()
    adjusted = generate_learning_path("根据练习提交结果调整：加强评价指标与迁移练习")
    assessment_report = AssessmentReport(
        id=f"assess_{uuid4().hex[:8]}",
        score=score,
        mastery_delta=delta,
        strengths=["能识别训练/测试拆分", "能用例子解释模型评价"],
        weak_points=profile.weak_points,
        mistake_patterns=profile.mistake_patterns,
        feedback="建议下一轮先复习评价指标，再完成代码案例中的预测解释任务。",
        adjusted_path=adjusted,
        created_at=now(),
    )
    save_record("profile", profile.id, profile.model_dump())
    save_record("assessment", assessment_report.id, assessment_report.model_dump())
    return assessment_report


def hydrate_from_db():
    global resources
    loaded = load_records("resource")
    if loaded:
        from .schemas import Resource

        resources = [Resource(**item) for item in loaded]

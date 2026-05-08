from typing import Any, Literal

from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    ok: bool = True
    data: Any | None = None
    error: dict[str, Any] | None = None


class Profile(BaseModel):
    id: str = "student_demo"
    major: str = "计算机科学与技术"
    education_level: str = "本科二年级"
    course: str = "人工智能导论"
    current_chapter: str = "机器学习基础"
    knowledge_base: list[str] = Field(default_factory=lambda: ["Python 基础", "线性代数薄弱"])
    learning_goal: str = "理解机器学习核心概念并完成课程项目"
    cognitive_style: str = "例子驱动"
    preferred_modalities: list[str] = Field(default_factory=lambda: ["图解", "代码案例", "短视频"])
    time_budget: str = "每天 45 分钟"
    weak_points: list[str] = Field(default_factory=lambda: ["梯度下降", "模型评估指标"])
    mistake_patterns: list[str] = Field(default_factory=lambda: ["概念混淆", "公式不会迁移"])
    interests: list[str] = Field(default_factory=lambda: ["智能教育", "机器学习应用"])
    mastery: float = 0.42
    version: int = 1
    updated_at: str = ""


class ProfileChatRequest(BaseModel):
    message: str


class ProfileChatResponse(BaseModel):
    profile: Profile
    extracted: dict[str, Any]
    suggested_next_question: str
    version_change: str


class GenerateRequest(BaseModel):
    course: str = "人工智能导论"
    chapter: str = "机器学习基础"
    goal: str = "掌握核心概念并完成练习"
    pain_points: list[str] = Field(default_factory=list)


class AgentTrace(BaseModel):
    id: str
    job_id: str
    agent: str
    status: Literal["pending", "running", "completed", "failed"]
    input_summary: str
    output_summary: str
    source_refs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: float = 0.8
    started_at: str
    finished_at: str | None = None


class Resource(BaseModel):
    id: str
    type: str
    title: str
    content_format: Literal["markdown", "mermaid", "json", "code"]
    content: str
    source_refs: list[str]
    difficulty: str
    target_profile: list[str]
    review_status: Literal["passed", "needs_revision", "blocked"]
    created_by_agents: list[str]
    created_at: str


class GenerationJob(BaseModel):
    id: str
    status: Literal["queued", "running", "completed", "failed"]
    progress: int = 0
    current_step: str = "queued"
    request: GenerateRequest
    traces: list[AgentTrace] = Field(default_factory=list)
    resources: list[Resource] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str
    completed_at: str | None = None


class LearningPathStep(BaseModel):
    id: str
    title: str
    objective: str
    recommended_resource_ids: list[str]
    reason: str
    estimated_minutes: int
    status: Literal["todo", "doing", "done"] = "todo"


class LearningPath(BaseModel):
    id: str
    profile_version: int
    mastery: float
    steps: list[LearningPathStep]
    adjustment_reason: str
    updated_at: str


class TutorRequest(BaseModel):
    question: str
    resource_id: str | None = None


class TutorResponse(BaseModel):
    answer: str
    source_refs: list[str]
    mermaid: str


class QuizSubmitRequest(BaseModel):
    answers: list[str]
    resource_id: str | None = None


class AssessmentReport(BaseModel):
    id: str
    score: int
    mastery_delta: float
    strengths: list[str]
    weak_points: list[str]
    mistake_patterns: list[str]
    feedback: str
    adjusted_path: LearningPath
    created_at: str

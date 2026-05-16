from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ApiResponse(BaseModel):
    ok: bool = True
    data: Any | None = None
    error: dict[str, Any] | None = None


class Profile(BaseModel):
    id: str = "student_demo"
    major: str = ""
    education_level: str = ""
    course: str = "人工智能导论"
    current_chapter: str = ""
    knowledge_base: list[str] = Field(default_factory=list)
    learning_goal: str = ""
    cognitive_style: str = ""
    preferred_modalities: list[str] = Field(default_factory=list)
    time_budget: str = ""
    weak_points: list[str] = Field(default_factory=list)
    mistake_patterns: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    mastery: float = 0.0
    version: int = 1
    updated_at: str = ""


class ProfileChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class ProfileChatResponse(BaseModel):
    profile: Profile
    extracted: dict[str, Any]
    suggested_next_question: str
    version_change: str


class GenerateRequest(BaseModel):
    course: str = Field(default="人工智能导论", min_length=1, max_length=80)
    chapter: str = Field(default="机器学习基础", min_length=1, max_length=80)
    goal: str = Field(default="掌握核心概念并完成练习", min_length=1, max_length=200)
    pain_points: list[str] = Field(default_factory=list, max_length=10)
    resource_types: list[str] = Field(default_factory=list, max_length=12)


class AgentTrace(BaseModel):
    id: str
    job_id: str
    agent: str
    status: Literal["pending", "running", "completed", "failed"]
    input_summary: str
    output_summary: str
    collaboration_stage: str = ""
    boundary: str = ""
    depends_on: list[str] = Field(default_factory=list)
    source_refs: list[Any] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: float = 0.8
    retry_count: int = 0
    llm_provider: str = ""
    arbitration_note: str = ""
    review_conclusion: str = ""
    started_at: str
    finished_at: str | None = None


class EvidenceSource(BaseModel):
    id: str
    text: str = ""
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = ""


class Resource(BaseModel):
    id: str
    type: str
    title: str
    content_format: Literal["markdown", "mermaid", "json", "code"]
    content: str
    evidence_sources: list[EvidenceSource] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    difficulty: str
    target_profile: list[str]
    personalized_reason: str = ""
    review_status: Literal["passed", "needs_revision", "blocked"]
    review_reason: str = ""
    audit_reason: str = ""
    review_notes: list[str] = Field(default_factory=list)
    review_confidence: float = 0.0
    user_feedback: Literal["neutral", "favorite", "hidden"] = "neutral"
    created_by_agents: list[str]
    created_at: str

    @model_validator(mode="after")
    def sync_evidence_and_legacy_refs(self):
        if self.evidence_sources and not self.source_refs:
            self.source_refs = [source.id for source in self.evidence_sources]
        elif self.source_refs and not self.evidence_sources:
            self.evidence_sources = [EvidenceSource(id=ref) for ref in self.source_refs]
        return self


class PlanDecision(BaseModel):
    resource_type: str
    priority: float
    difficulty: str
    reason: str


class PlanSummary(BaseModel):
    total_estimated_time: int = 0
    decisions: list[PlanDecision] = Field(default_factory=list)


class GenerationJob(BaseModel):
    id: str
    status: Literal["queued", "running", "completed", "failed"]
    progress: int = 0
    current_step: str = "queued"
    request: GenerateRequest
    plan_summary: PlanSummary = Field(default_factory=PlanSummary)
    traces: list[AgentTrace] = Field(default_factory=list)
    resources: list[Resource] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    fallback_reason: str = ""
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
    question: str = Field(min_length=1, max_length=1000)
    resource_id: str | None = None
    history: list[dict[str, str]] = Field(default_factory=list, max_length=12)


class WeakPointConfirmRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=80)
    evidence: str = Field(default="", max_length=300)


class TutorExerciseSubmitRequest(BaseModel):
    exercise: dict[str, Any]
    answer: str = Field(min_length=1, max_length=1000)


class TutorResponse(BaseModel):
    answer: str
    source_refs: list[str]
    mermaid: str


class QuizSubmitRequest(BaseModel):
    answers: list[str] = Field(min_length=1, max_length=20)
    resource_id: str | None = None


class ResourceFeedbackRequest(BaseModel):
    resource_id: str
    action: Literal["neutral", "favorite", "hidden"]


class ChatAndGenerateRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    regenerate_resources: bool = True
    resource_types: list[str] = Field(default_factory=list)


class ResourceAdjustRequest(BaseModel):
    resource_id: str | None = None
    adjustments: list[dict[str, Any]] = Field(default_factory=list)
    preferences: dict[str, Any] = Field(default_factory=dict)
    target_concepts: list[str] = Field(default_factory=list)


class IncrementalUpdateResponse(BaseModel):
    ok: bool = True
    profile_updated: bool = False
    resources_updated: bool = False
    learning_path_updated: bool = False
    message: str = ""
    updated_profile: Profile | None = None
    updated_resources: list[Resource] = Field(default_factory=list)
    updated_learning_path: LearningPath | None = None


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

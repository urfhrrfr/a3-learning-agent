import json
import os

from fastapi.testclient import TestClient
from pathlib import Path
from uuid import uuid4

os.environ.setdefault("LLM_PROVIDER", "mock")

from app import state, storage
from app.agents import KnowledgeAgent, ProfileAgent, ReviewAgent, WorkflowState
from app.knowledge import COURSE, question_bank
from app.main import app
from app.path_planner import PathPlanner
from app.providers.factory import get_llm_provider
from app.providers.mock_llm import MockLLMProvider
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.providers.spark_llm import SparkLLMProvider
from app.schemas import GenerateRequest, Profile, Resource


client = TestClient(app)


class SemanticFusionLLM(MockLLMProvider):
    name = "semantic-test"

    def complete(self, prompt: str) -> str:
        assert "旧画像 JSON" in prompt
        assert "学生最新自然语言对话" in prompt
        return json.dumps(
            {
                "id": "student_demo",
                "major": "计算机科学与技术",
                "education_level": "本科二年级",
                "course": "人工智能导论",
                "current_chapter": "机器学习基础",
                "knowledge_base": ["Python"],
                "learning_goal": "完成课程项目",
                "cognitive_style": "例子驱动",
                "preferred_modalities": ["代码案例"],
                "time_budget": "每天40分钟",
                "weak_points": ["线性代数"],
                "mistake_patterns": [],
                "interests": ["机器学习应用"],
                "mastery": 0.42,
                "version": 99,
                "updated_at": "should-be-preserved",
            },
            ensure_ascii=False,
        )


def payload(response):
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "data" in body
    assert body["error"] is None
    return body["data"]


def error_payload(response, status_code):
    assert response.status_code == status_code
    body = response.json()
    assert body["ok"] is False
    assert body["data"] is None
    assert_fields(body["error"], {"code", "message", "details"})
    return body["error"]


def assert_fields(data, fields):
    for field in fields:
        assert field in data


PROFILE_FIELDS = {
    "id",
    "major",
    "education_level",
    "course",
    "current_chapter",
    "knowledge_base",
    "learning_goal",
    "cognitive_style",
    "preferred_modalities",
    "time_budget",
    "weak_points",
    "mistake_patterns",
    "interests",
    "mastery",
    "version",
    "updated_at",
}

RESOURCE_FIELDS = {
    "id",
    "type",
    "title",
    "content_format",
    "content",
    "source_refs",
    "difficulty",
    "target_profile",
    "review_status",
    "review_reason",
    "audit_reason",
    "review_notes",
    "review_confidence",
    "created_by_agents",
    "created_at",
}

JOB_FIELDS = {
    "id",
    "status",
    "progress",
    "current_step",
    "request",
    "traces",
    "resources",
    "events",
    "created_at",
    "completed_at",
}

PATH_FIELDS = {
    "id",
    "profile_version",
    "mastery",
    "steps",
    "adjustment_reason",
    "updated_at",
}

ASSESSMENT_FIELDS = {
    "id",
    "score",
    "mastery_delta",
    "strengths",
    "weak_points",
    "mistake_patterns",
    "feedback",
    "adjusted_path",
    "created_at",
}


def test_course_knowledge_base_has_rich_question_metadata():
    assert len(COURSE["chapters"]) == 12
    assert len(COURSE["code_cases"]) >= 6

    for chapter in COURSE["chapters"]:
        assert len(chapter["objectives"]) >= 5
        assert len(chapter["concepts"]) >= 4
        assert len(chapter["concept_cards"]) >= 4
        assert len(chapter["detailed_concepts"]) >= 4
        assert len(chapter["difficulties"]) >= 5
        assert len(chapter["misconceptions"]) >= 5
        assert len(chapter["code_labs"]) >= 3
        assert len(chapter["practice_questions"]) == 5
        for question in chapter["practice_questions"]:
            assert_fields(
                question,
                {"standard_answer", "explanation", "difficulty", "assessment_point", "rubric"},
            )
            assert question["rubric"]

    questions = question_bank()
    assert len(questions) == 60
    assert_fields(
        questions[0],
        {"answer", "analysis", "difficulty", "assessment_point", "options", "rubric"},
    )


def test_profile_chat_updates_profile():
    data = payload(client.post("/api/profile/chat", json={"message": "我线性代数薄弱，希望多给 Python 代码案例"}))
    assert data["profile"]["version"] >= 2
    assert "代码案例" in data["profile"]["preferred_modalities"]


def test_profile_fuse_uses_llm_semantic_profile_json():
    current = state.Profile(
        knowledge_base=["Python基础", "Python 基础"],
        learning_goal="通过期末考试",
        preferred_modalities=["图解"],
        time_budget="每天30分钟",
        weak_points=[],
        updated_at=state.now(),
    )
    agent = ProfileAgent(SemanticFusionLLM())

    fused, conflicts, reasoning = agent.fuse(
        current,
        latest_message="Python还可以，但线性代数不太好，最近每天大概能学40分钟，希望做课程项目。",
    )

    assert fused.knowledge_base == ["Python"]
    assert fused.learning_goal == "完成课程项目"
    assert fused.time_budget == "每天40分钟"
    assert "线性代数" in fused.weak_points
    assert fused.version == current.version
    assert fused.updated_at == current.updated_at
    assert "LLM语义融合完成" in reasoning
    assert set(conflicts) >= {"knowledge_base", "learning_goal", "time_budget", "weak_points"}


def test_generation_returns_resources_and_trace():
    data = payload(
        client.post(
            "/api/resources/generate",
            json={"course": "人工智能导论", "chapter": "机器学习基础", "goal": "理解泛化与过拟合", "pain_points": ["公式迁移"]},
        )
    )
    assert data["status"] == "completed"
    assert data["events"][0]["type"] == "job_queued"
    assert data["events"][-1]["type"] == "job_completed"
    assert len(data["resources"]) >= 6
    assert len(data["traces"]) >= 8
    assert all("input_summary" in item and "output_summary" in item for item in data["traces"])
    assert all("source_refs" in item and "confidence" in item for item in data["traces"])
    assert all("collaboration_stage" in item and "boundary" in item for item in data["traces"])
    assert all("retry_count" in item and "arbitration_note" in item for item in data["traces"])
    assert all(item["llm_provider"] == "mock" for item in data["traces"])
    assert all(item["source_refs"] for item in data["resources"])
    assert all(item["review_reason"] for item in data["resources"])
    assert all(item["audit_reason"] for item in data["resources"])
    assert all(item["review_notes"] for item in data["resources"])
    assert all(0 <= item["review_confidence"] <= 1 for item in data["resources"])

    resources_by_type = {item["type"]: item for item in data["resources"]}
    lecture = resources_by_type["lecture_doc"]["content"]
    quiz = json.loads(resources_by_type["quiz"]["content"])
    media_script = resources_by_type["media_script"]["content"]
    code_case = resources_by_type["code_case"]["content"]

    assert "核心概念速查" in lecture
    assert "| 概念 | 一句话解释 | 学习时要抓住 |" in lecture
    assert len(quiz) >= 4
    assert all("answer" in item for item in quiz)
    assert all("difficulty" in item and "assessment_point" in item for item in quiz)
    assert all("rubric" in item for item in quiz)
    assert any("options" in item for item in quiz)
    assert "分镜脚本" in media_script
    assert "| 时间 | 画面 | 旁白 | 屏幕文字 |" in media_script
    assert "思考题" in code_case


def test_knowledge_agent_reranks_sources_with_profile_context():
    profile = Profile(
        learning_goal="理解泛化与过拟合",
        weak_points=["过拟合", "公式迁移"],
        mistake_patterns=["概念混淆"],
        updated_at=state.now(),
    )
    request = GenerateRequest(
        course="人工智能导论",
        chapter="机器学习基础",
        goal="理解泛化与过拟合",
        pain_points=["公式迁移"],
    )
    workflow_state = WorkflowState("job_knowledge_test", request, profile)
    workflow_state.current_query = "为什么训练集表现很好，但新数据效果很差？"

    result = KnowledgeAgent(MockLLMProvider()).run(workflow_state)

    assert "语义检索到" in result["summary"]
    assert 3 <= len(workflow_state.sources) <= 5
    assert all({"id", "text", "relevance_score"} <= set(item) for item in workflow_state.sources)
    assert all(0 <= item["relevance_score"] <= 1 for item in workflow_state.sources)
    assert any("过拟合" in item["text"] or "泛化" in item["text"] for item in workflow_state.sources)


def test_quiz_submit_creates_assessment_and_path():
    data = payload(client.post("/api/quiz/submit", json={"answers": ["过拟合会导致泛化下降"], "resource_id": None}))
    assert data["score"] >= 80
    assert data["adjusted_path"]["steps"]
    assert "下一步建议" in data["feedback"]
    assert data["adjusted_path"]["steps"][0]["reason"]


def test_path_planner_changes_path_by_profile_mastery_and_preferences():
    planner = PathPlanner(MockLLMProvider())
    resources = [
        {"id": "diagram_overfit", "type": "mindmap", "title": "过拟合概念图解", "difficulty": "入门", "estimated_time_minutes": 15},
        {"id": "code_gradient", "type": "code_case", "title": "梯度下降代码实验", "difficulty": "提高", "estimated_time_minutes": 35},
        {"id": "video_metrics", "type": "media_script", "title": "评价指标短视频脚本", "difficulty": "基础", "estimated_time_minutes": 20},
    ]
    beginner = state.Profile(
        mastery=0.22,
        weak_points=["过拟合"],
        preferred_modalities=["图解"],
        mistake_patterns=["概念混淆"],
        updated_at=state.now(),
    )
    advanced = state.Profile(
        mastery=0.78,
        weak_points=["梯度下降"],
        preferred_modalities=["代码案例"],
        mistake_patterns=["公式迁移不足"],
        updated_at=state.now(),
    )

    beginner_path = planner.plan(beginner, resources)["learning_path"]
    advanced_path = planner.plan(advanced, resources)["learning_path"]

    assert beginner_path["steps"][0]["title"].startswith("入门")
    assert advanced_path["steps"][0]["title"].startswith("提高")
    assert beginner_path["steps"][0]["recommended_resources"][0]["id"] == "diagram_overfit"
    assert advanced_path["steps"][0]["recommended_resources"][0]["id"] == "code_gradient"
    assert beginner_path["steps"][0]["reason"] != advanced_path["steps"][0]["reason"]


def test_learning_path_api_exposes_specific_reasons_and_resource_ids(monkeypatch):
    original_profile = state.profile
    original_resources = state.resources
    original_path = state.learning_path
    original_assessment = state.assessment_report
    try:
        state.profile = state.Profile(
            mastery=0.28,
            weak_points=["过拟合"],
            preferred_modalities=["图解"],
            mistake_patterns=["概念混淆"],
            updated_at=state.now(),
        )
        state.resources = [
            Resource(
                id="res_diagram_overfit",
                type="mindmap",
                title="过拟合图解",
                content_format="mermaid",
                content="flowchart LR\nA-->B",
                source_refs=["ai_intro/ch04#concepts"],
                difficulty="入门",
                target_profile=["图解"],
                review_status="passed",
                created_by_agents=["TestAgent"],
                created_at=state.now(),
            )
        ]
        state.learning_path = None
        state.assessment_report = None

        generated_path = payload(client.post("/api/learning-path/generate"))

        first_step = generated_path["steps"][0]
        assert first_step["recommended_resource_ids"] == ["res_diagram_overfit"]
        assert "当前掌握度 0.28" in first_step["reason"]
        assert "图解" in first_step["reason"]
    finally:
        state.profile = original_profile
        state.resources = original_resources
        state.learning_path = original_path
        state.assessment_report = original_assessment


def test_api_contract_endpoints_return_documented_shapes():
    health = payload(client.get("/api/health"))
    assert_fields(health, {"status", "mock_llm", "course"})
    assert health["llm_provider"] == "mock"

    profile = payload(client.get("/api/profile/current"))
    assert_fields(profile, PROFILE_FIELDS)

    profile_chat = payload(client.post("/api/profile/chat", json={"message": "Python"}))
    assert_fields(profile_chat, {"profile", "extracted", "suggested_next_question", "version_change"})
    assert_fields(profile_chat["profile"], PROFILE_FIELDS)

    job = payload(
        client.post(
            "/api/resources/generate",
            json={"course": "AI", "chapter": "ML", "goal": "contract test", "pain_points": ["metrics"]},
        )
    )
    assert_fields(job, JOB_FIELDS)
    assert job["status"] == "completed"
    assert job["progress"] == 100
    assert job["resources"]

    fetched_job = payload(client.get(f"/api/jobs/{job['id']}"))
    assert_fields(fetched_job, JOB_FIELDS)
    assert fetched_job["id"] == job["id"]

    resources = payload(client.get("/api/resources"))
    assert isinstance(resources, list)
    assert resources
    assert_fields(resources[0], RESOURCE_FIELDS)

    resource = payload(client.get(f"/api/resources/{resources[0]['id']}"))
    assert_fields(resource, RESOURCE_FIELDS)
    assert resource["id"] == resources[0]["id"]

    generated_path = payload(client.post("/api/learning-path/generate"))
    assert_fields(generated_path, PATH_FIELDS)
    assert generated_path["steps"]

    current_path = payload(client.get("/api/learning-path/current"))
    assert_fields(current_path, PATH_FIELDS)
    assert current_path["steps"]

    tutor = payload(client.post("/api/tutor/chat", json={"question": "What is overfitting?", "resource_id": None}))
    assert_fields(tutor, {"answer", "source_refs", "mermaid"})

    assessment = payload(client.post("/api/quiz/submit", json={"answers": ["generalization"], "resource_id": None}))
    assert_fields(assessment, ASSESSMENT_FIELDS)
    assert_fields(assessment["adjusted_path"], PATH_FIELDS)

    report = payload(client.get("/api/assessment/report"))
    assert_fields(report, ASSESSMENT_FIELDS)


def test_error_responses_use_api_envelope():
    job_error = error_payload(client.get("/api/jobs/not_found"), 404)
    assert job_error["code"] == "JOB_NOT_FOUND"
    assert job_error["message"] == "job not found"

    resource_error = error_payload(client.get("/api/resources/not_found"), 404)
    assert resource_error["code"] == "RESOURCE_NOT_FOUND"
    assert resource_error["message"] == "resource not found"

    validation_error = error_payload(client.post("/api/profile/chat", json={}), 422)
    assert validation_error["code"] == "VALIDATION_ERROR"

    empty_message_error = error_payload(client.post("/api/profile/chat", json={"message": ""}), 422)
    assert empty_message_error["code"] == "VALIDATION_ERROR"

    empty_quiz_error = error_payload(client.post("/api/quiz/submit", json={"answers": []}), 422)
    assert empty_quiz_error["code"] == "VALIDATION_ERROR"


def test_hydrate_from_db_restores_persisted_demo_state(monkeypatch):
    original_profile = state.profile
    original_jobs = state.jobs
    original_resources = state.resources
    original_path = state.learning_path
    original_assessment = state.assessment_report

    test_db = Path(__file__).resolve().parents[1] / "data" / f"test_app_hydrate_{uuid4().hex}.db"
    monkeypatch.setattr(storage, "DB_PATH", test_db)
    try:
        state.profile = state.Profile(updated_at=state.now())
        state.jobs = {}
        state.resources = []
        state.learning_path = None
        state.assessment_report = None

        state.update_profile_from_message("我想多看 Python 代码案例")
        job = state.run_generation(
            state.GenerateRequest(
                course="人工智能导论",
                chapter="机器学习基础",
                goal="理解泛化与过拟合",
                pain_points=["评价指标混淆"],
            )
        )
        report = state.submit_quiz(state.QuizSubmitRequest(answers=["过拟合会导致泛化下降"]))

        state.profile = state.Profile(updated_at=state.now())
        state.jobs = {}
        state.resources = []
        state.learning_path = None
        state.assessment_report = None

        state.hydrate_from_db()

        assert state.profile.version >= 2
        assert job.id in state.jobs
        assert state.jobs[job.id].status == "completed"
        assert len(state.resources) >= 6
        assert state.learning_path is not None
        assert state.assessment_report is not None
        assert state.assessment_report.id == report.id
    finally:
        state.profile = original_profile
        state.jobs = original_jobs
        state.resources = original_resources
        state.learning_path = original_path
        state.assessment_report = original_assessment


def test_llm_provider_factory_uses_mock_by_default(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert isinstance(get_llm_provider(), MockLLMProvider)


def test_llm_provider_factory_supports_spark_and_compatible_aliases(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "spark")
    assert isinstance(get_llm_provider(), SparkLLMProvider)

    for provider in ["openai", "openai_compatible", "deepseek", "qwen", "dashscope"]:
        monkeypatch.setenv("LLM_PROVIDER", provider)
        assert isinstance(get_llm_provider(), OpenAICompatibleProvider)


def test_review_agent_marks_passed_needs_revision_and_blocked():
    workflow = WorkflowState(
        job_id="job_review_test",
        request=state.GenerateRequest(chapter="机器学习基础", goal="理解训练集、泛化和过拟合"),
        profile=state.Profile(updated_at=state.now()),
    )
    chapter_id = workflow.chapter["id"]
    workflow.resources = [
        Resource(
            id="res_pass",
            type="lecture_doc",
            title="训练集、泛化和过拟合讲解",
            content_format="markdown",
            content=(
                "训练集用于学习规律，泛化关注新数据表现。损失函数用于衡量预测差距，"
                "过拟合会导致测试表现下降，需要结合机器学习基础中的方法适用条件、概念边界和案例分析。"
            ),
            source_refs=[f"{chapter_id}#detailed_concepts", f"{chapter_id}#misconceptions"],
            difficulty="入门",
            target_profile=["例子驱动"],
            review_status="needs_revision",
            created_by_agents=["LectureAgent"],
            created_at=state.now(),
        ),
        Resource(
            id="res_missing_source",
            type="reading",
            title="泛化阅读",
            content_format="markdown",
            content="训练集和泛化相关，但是没有来源。",
            source_refs=[],
            difficulty="入门",
            target_profile=["阅读材料"],
            review_status="needs_revision",
            created_by_agents=["ReadingAgent"],
            created_at=state.now(),
        ),
        Resource(
            id="res_invalid_source",
            type="quiz",
            title="无关练习",
            content_format="json",
            content='[{"question":"今天午饭吃什么","answer":"无关"}]',
            source_refs=[f"{chapter_id}#not_exist"],
            difficulty="入门",
            target_profile=["练习"],
            review_status="needs_revision",
            created_by_agents=["QuizAgent"],
            created_at=state.now(),
        ),
        Resource(
            id="res_blocked",
            type="lecture_doc",
            title="风险内容",
            content_format="markdown",
            content="训练集 泛化 违法 内容",
            source_refs=[f"{chapter_id}#detailed_concepts"],
            difficulty="入门",
            target_profile=["例子驱动"],
            review_status="needs_revision",
            created_by_agents=["LectureAgent"],
            created_at=state.now(),
        ),
    ]

    result = ReviewAgent(MockLLMProvider()).run(workflow)

    resources = {resource.id: resource for resource in workflow.resources}
    assert resources["res_pass"].review_status == "passed"
    assert resources["res_pass"].review_confidence >= 0.8
    assert resources["res_pass"].audit_reason
    assert resources["res_pass"].review_notes

    assert resources["res_missing_source"].review_status == "needs_revision"
    assert "缺少 source_refs" in resources["res_missing_source"].audit_reason

    assert resources["res_invalid_source"].review_status == "needs_revision"
    assert "无效来源引用" in "；".join(resources["res_invalid_source"].review_notes)

    assert resources["res_blocked"].review_status == "blocked"
    assert resources["res_blocked"].review_confidence == 0.35
    assert "blocked=1" in result["summary"]

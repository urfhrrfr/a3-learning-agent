import json
import os

from fastapi.testclient import TestClient
from uuid import uuid4

os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ["MYSQL_URL"] = ""
os.environ["DATABASE_URL"] = ""
os.environ["REDIS_URL"] = ""
os.environ.setdefault("VECTOR_STORE", "memory")

from app import cache, state, storage
from app.agents import KnowledgeAgent, Orchestrator, PlannerAgent, ProfileAgent, ReviewAgent, WorkflowState
from app.core.profile_normalizer import ProfileNormalizer
from app.core.profile_validator import ProfileValidator
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
                "profile": {
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
                "changed_fields": ["knowledge_base", "learning_goal", "time_budget", "weak_points"],
                "conflicts": [
                    {
                        "field": "time_budget",
                        "before": "每天30分钟",
                        "after": "每天40分钟",
                        "reason": "最新对话优先",
                    }
                ],
                "merge_reasoning": "合并 Python 近义标签，并将线性代数不太好识别为薄弱点。",
                "confidence": 0.91,
            },
            ensure_ascii=False,
        )


class ReviewFactCheckLLM(MockLLMProvider):
    name = "review-test"

    def __init__(self):
        self.calls = 0

    def complete(self, prompt: str) -> str:
        self.calls += 1
        assert "待审核内容" in prompt
        assert "关键事实点" in prompt
        return json.dumps(
            {
                "is_accurate": False,
                "reasoning": "测试模型认为内容需要复核",
                "confidence": 0.88,
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
    "plan_summary",
    "traces",
    "resources",
    "events",
    "created_at",
    "completed_at",
}

HISTORY_SUMMARY_FIELDS = {
    "id",
    "status",
    "progress",
    "current_step",
    "request",
    "plan_summary",
    "fallback_reason",
    "created_at",
    "completed_at",
    "is_current",
    "resource_count",
    "resource_type_counts",
    "trace_count",
    "event_count",
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
    assert data["fusion_meta"]["source"] in {"fallback", "llm"}


def test_tutor_suggests_and_confirms_weak_point_from_profile_signal():
    headers = {"X-User-Id": f"tutor-tier2-{uuid4().hex[:8]}"}
    payload(client.post("/api/profile/chat", json={"message": "我喜欢图解方式"}, headers=headers))

    tutor = payload(client.post("/api/tutor/chat", json={"question": "我还是不懂梯度下降"}, headers=headers))

    assert tutor["profile_suggestion"]["topic"] == "梯度下降"
    assert tutor["profile_suggestion"]["already_exists"] is False
    assert tutor["personalization"]["preferred_mode"] == "图解"
    assert "梯度下降" not in tutor["profile_snapshot"]["weak_points"]

    confirmed = payload(
        client.post(
            "/api/profile/weak-points/confirm",
            json={"topic": "梯度下降", "evidence": tutor["profile_suggestion"]["message"]},
            headers=headers,
        )
    )

    assert confirmed["profile_updated"] is True
    assert "梯度下降" in confirmed["profile"]["weak_points"]

    repeated = payload(client.post("/api/tutor/chat", json={"question": "我还是不懂梯度下降"}, headers=headers))
    assert repeated["profile_suggestion"]["already_exists"] is True


def test_tutor_learning_loop_generates_exercise_and_updates_mastery():
    headers = {"X-User-Id": f"tutor-loop-{uuid4().hex[:8]}"}
    payload(client.post("/api/profile/chat", json={"message": "我喜欢代码案例，梯度下降有点弱"}, headers=headers))

    tutor = payload(client.post("/api/tutor/chat", json={"question": "我还是不懂梯度下降"}, headers=headers))

    assert tutor["exercise"]["topic"] == "梯度下降"
    assert tutor["next_step"]["title"]
    assert "cited_resources" in tutor

    before = payload(client.get("/api/profile/current", headers=headers))
    result = payload(
        client.post(
            "/api/tutor/exercise/submit",
            json={
                "exercise": tutor["exercise"],
                "answer": "负梯度方向会让损失下降，学习率控制每一步更新的大小。",
            },
            headers=headers,
        )
    )

    assert result["score"] >= 80
    assert result["profile"]["mastery"] > before["mastery"]
    assert result["learning_path"]["steps"]
    assert result["next_step"]["title"]


def test_tutor_chat_uses_rag_evidence_without_generated_resources():
    original_resources = state.resources
    headers = {"X-User-Id": f"tutor-rag-{uuid4().hex[:8]}"}
    try:
        state.resources = []
        payload(client.post("/api/profile/chat", json={"message": "我喜欢代码案例，过拟合和泛化容易混淆"}, headers=headers))

        tutor = payload(
            client.post(
                "/api/tutor/chat",
                json={"question": "为什么训练集表现很好，测试集效果可能很差？"},
                headers=headers,
            )
        )

        assert tutor["source_refs"]
        assert tutor["evidence_sources"]
        assert tutor["cited_resources"] == []
        assert all(source["text"] for source in tutor["evidence_sources"])
        assert set(tutor["source_refs"]) >= {source["id"] for source in tutor["evidence_sources"]}
        assert tutor["retrieval_warnings"] == []
        assert any("vector" in source.get("retrieval_channels", []) for source in tutor["evidence_sources"])
    finally:
        state.resources = original_resources


def test_retrieval_logs_persist_generation_and_tutor_evidence(monkeypatch, tmp_path):
    original_resources = state.resources
    test_db = tmp_path / f"test_retrieval_logs_{uuid4().hex}.db"
    monkeypatch.setattr(storage, "DB_PATH", test_db)
    try:
        state.resources = []
        workflow = WorkflowState(
            "job_retrieval_log_test",
            GenerateRequest(chapter="机器学习基础", goal="理解过拟合", pain_points=["泛化混淆"]),
            Profile(updated_at=state.now(), weak_points=["过拟合"], preferred_modalities=["代码案例"]),
        )

        KnowledgeAgent(MockLLMProvider()).run(workflow)

        generation_logs = storage.load_records("retrieval_log")
        assert len(generation_logs) == 1
        assert generation_logs[0]["scenario"] == "resource_generation"
        assert generation_logs[0]["job_id"] == "job_retrieval_log_test"
        assert generation_logs[0]["selected_sources"]
        assert generation_logs[0]["selected_source_ids"]

        headers = {"X-User-Id": f"retrieval-log-user-{uuid4().hex[:8]}"}
        tutor = payload(
            client.post(
                "/api/tutor/chat",
                json={"question": "为什么训练集很好但测试集很差？"},
                headers=headers,
            )
        )
        assert tutor["evidence_sources"]

        logs = payload(client.get("/api/retrieval/logs?limit=10"))
        scenarios = {item["scenario"] for item in logs}
        assert {"resource_generation", "tutor_chat"} <= scenarios
        tutor_log = next(item for item in logs if item["scenario"] == "tutor_chat")
        assert tutor_log["user_id"] == headers["X-User-Id"]
        assert tutor_log["query"] == "为什么训练集很好但测试集很差？"
        assert tutor_log["selected_sources"]
    finally:
        state.resources = original_resources
        if test_db.exists():
            try:
                test_db.unlink()
            except PermissionError:
                pass


def test_profile_normalizer_static_aliases_and_injection():
    normalizer = ProfileNormalizer({"高数": "高等数学", "python基础": "Python", "代码": "代码案例"})

    assert normalizer.normalize_tags([" 高数 ", "高等数学", "PYTHON 基础", "代码"]) == ["高等数学", "Python", "代码案例"]

    agent = ProfileAgent(MockLLMProvider(), normalizer=normalizer)
    current = state.Profile(knowledge_base=["高数"], preferred_modalities=[], updated_at=state.now())
    fused, _, _ = agent.fuse(
        current,
        {"extracted": {"knowledge_base": ["高等数学", "Python 基础"], "preferred_modalities": ["代码"]}},
    )

    assert fused.knowledge_base == ["高等数学", "Python"]
    assert fused.preferred_modalities == ["代码案例"]


def test_profile_validator_accepts_supported_fusion():
    old_profile = state.Profile(
        learning_goal="通过期末考试",
        weak_points=["线性代数", "梯度下降"],
        preferred_modalities=["图解", "代码案例"],
        updated_at=state.now(),
    ).model_dump()
    new_profile = state.Profile(
        learning_goal="完成课程项目",
        weak_points=["线性代数", "梯度下降", "模型评估指标"],
        preferred_modalities=["图解", "代码案例"],
        updated_at=state.now(),
    ).model_dump()

    result = ProfileValidator().evaluate_fusion(old_profile, new_profile, "我想完成课程项目，评估指标也容易混淆")

    assert result["is_valid"] is True
    assert result["confidence_score"] >= 0.75
    assert result["requires_confirmation"] is False


def test_profile_validator_detects_cliff_drop_and_empty_fields():
    old_profile = state.Profile(
        learning_goal="完成课程项目",
        weak_points=["线性代数", "梯度下降", "模型评估指标"],
        preferred_modalities=["图解", "代码案例", "短视频"],
        updated_at=state.now(),
    ).model_dump()
    new_profile = {**old_profile, "learning_goal": "", "weak_points": [], "preferred_modalities": ["图解"]}

    result = ProfileValidator().evaluate_fusion(old_profile, new_profile, "我最近每天40分钟")

    assert result["is_valid"] is False
    assert result["requires_confirmation"] is True
    assert any("weak_points" in warning and "疑似画像信息丢失" in warning for warning in result["warnings"])
    assert any("learning_goal 被清空" in warning for warning in result["warnings"])


def test_profile_validator_detects_unknown_tags_and_bad_mastery():
    old_profile = state.Profile(updated_at=state.now()).model_dump()
    new_profile = {
        **old_profile,
        "preferred_modalities": ["星际传送门学习法"],
        "mistake_patterns": ["!!!"],
        "mastery": 1.4,
    }

    result = ProfileValidator().evaluate_fusion(old_profile, new_profile, "我想多看代码案例")

    assert result["is_valid"] is False
    assert result["requires_confirmation"] is True
    assert any("未知或异常标签" in warning for warning in result["warnings"])
    assert any("mastery 应为 0-1" in warning for warning in result["warnings"])


def test_profile_versions_return_persisted_snapshots(monkeypatch, tmp_path):
    original_profile = state.profile
    test_db = tmp_path / f"test_profile_versions_{uuid4().hex}.db"
    monkeypatch.setattr(storage, "DB_PATH", test_db)
    try:
        state.profile = state.Profile(updated_at=state.now())
        first = state.update_profile_from_message("我想多看 Python 代码案例")
        second = state.update_profile_from_message("每天大概能学40分钟，线性代数不太好")

        versions = state.profile_versions()

        assert len(versions) >= 2
        assert versions[0]["version"] == state.profile.version
        assert {item["version"] for item in versions} >= {2, 3}
        assert first["fusion_meta"]["source"] == "fallback"
        assert second["fusion_meta"]["source"] == "fallback"

        rolled_back = state.rollback_profile_version(2)

        assert rolled_back is not None
        assert rolled_back["profile"]["version"] == 2
        assert state.profile.version == 2
        assert rolled_back["learning_path"]["profile_version"] == 2
    finally:
        state.profile = original_profile
        if test_db.exists():
            try:
                test_db.unlink()
            except PermissionError:
                pass


def test_profile_endpoints_are_isolated_by_user_id(monkeypatch, tmp_path):
    original_profile = state.profile
    original_profiles = dict(state.profiles)
    test_db = tmp_path / f"test_profile_users_{uuid4().hex}.db"
    monkeypatch.setattr(storage, "DB_PATH", test_db)
    try:
        state.profile = state.Profile(updated_at=state.now())
        state.profiles = {}
        user_a = {"X-User-Id": "anon-user-a"}
        user_b = {"X-User-Id": "anon-user-b"}

        first_a = payload(client.get("/api/profile/current", headers=user_a))
        first_b = payload(client.get("/api/profile/current", headers=user_b))
        assert first_a["id"] == "anon-user-a"
        assert first_b["id"] == "anon-user-b"
        assert payload(client.get("/api/profile/change-log", headers=user_a)) == []
        assert payload(client.get("/api/profile/change-log", headers=user_b)) == []

        updated_a = payload(client.post("/api/profile/chat", json={"message": "我想多看 Python 代码案例"}, headers=user_a))

        assert updated_a["profile"]["version"] == 2
        assert payload(client.get("/api/profile/change-log", headers=user_b)) == []
        assert payload(client.get("/api/profile/current", headers=user_b))["version"] == 1
        assert payload(client.get("/api/profile/versions", headers=user_a))[0]["version"] == 2
        assert payload(client.get("/api/profile/versions", headers=user_b))[0]["version"] == 1
    finally:
        state.profile = original_profile
        state.profiles = original_profiles
        if test_db.exists():
            try:
                test_db.unlink()
            except PermissionError:
                pass


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
    assert "线性代数不太好" in reasoning
    assert conflicts == ["time_budget: 每天30分钟 -> 每天40分钟；最新对话优先"]
    assert agent.last_fusion_meta["source"] == "llm"
    assert agent.last_fusion_meta["confidence"] == 0.91
    assert agent.last_fusion_meta["changed_fields"] == ["knowledge_base", "learning_goal", "time_budget", "weak_points"]
    assert "validation" in agent.last_fusion_meta


def test_profile_fallback_normalizes_synonyms_and_implicit_weakness():
    current = state.Profile(
        knowledge_base=["Python 基础"],
        preferred_modalities=["图解"],
        weak_points=[],
        updated_at=state.now(),
    )
    agent = ProfileAgent(MockLLMProvider())
    extraction = agent.extract("Python还可以，但线性代数不太好，想多看 Python 代码案例", current)

    fused, _, _ = agent.fuse(current, extraction, latest_message="Python还可以，但线性代数不太好，想多看 Python 代码案例")

    assert fused.knowledge_base.count("Python") == 1
    assert "线性代数薄弱" in fused.knowledge_base
    assert "线性代数" in fused.weak_points
    assert "代码案例" in fused.preferred_modalities
    assert agent.last_fusion_meta["source"] == "fallback"
    assert "validation" in agent.last_fusion_meta


def test_generation_returns_resources_and_trace():
    data = payload(
        client.post(
            "/api/resources/generate",
            json={
                "course": "人工智能导论",
                "chapter": "机器学习基础",
                "goal": "理解泛化与过拟合",
                "pain_points": ["公式迁移"],
                "resource_types": ["lecture_doc", "quiz", "media_script", "code_case"],
            },
        )
    )
    assert data["status"] == "completed"
    assert data["events"][0]["type"] == "job_queued"
    assert data["events"][-1]["type"] == "job_completed"
    assert len(data["resources"]) >= 4
    assert data["plan_summary"]["total_estimated_time"] > 0
    assert data["plan_summary"]["decisions"]
    assert_fields(data["plan_summary"]["decisions"][0], {"resource_type", "priority", "difficulty", "reason"})
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
    lecture_refs = resources_by_type["lecture_doc"]["source_refs"]
    quiz = json.loads(resources_by_type["quiz"]["content"])
    media_script = resources_by_type["media_script"]["content"]
    code_case = resources_by_type["code_case"]["content"]

    assert "核心概念速查" in lecture
    assert "| 概念 | 一句话解释 | 学习时要抓住 |" in lecture
    assert "## 检索依据" in lecture
    assert any(":" in ref for ref in lecture_refs)
    assert len(quiz) >= 4
    assert all("answer" in item for item in quiz)
    assert all("difficulty" in item and "assessment_point" in item for item in quiz)
    assert all("rubric" in item for item in quiz)
    assert all("source_id" in item for item in quiz)
    assert all("[来源:" in f"{item.get('question', '')}\n{item.get('explanation', '')}" for item in quiz)
    assert any("options" in item for item in quiz)
    assert "分镜脚本" in media_script
    assert "| 时间 | 画面 | 旁白 | 屏幕文字 |" in media_script
    assert "思考题" in code_case
    assert "[来源:" in code_case


def test_planner_agent_personalizes_resource_mix_by_profile():
    profile = state.Profile(
        mastery=0.24,
        preferred_modalities=["图解"],
        cognitive_style="例子驱动",
        time_budget="每天 20 分钟",
        weak_points=["概念混淆"],
        mistake_patterns=["术语混淆"],
        updated_at=state.now(),
    )
    request = state.GenerateRequest(
        chapter="机器学习基础",
        goal="先弄懂核心概念",
        pain_points=["概念混淆"],
    )
    workflow_state = WorkflowState("job_planner_test", request, profile)

    result = PlannerAgent(MockLLMProvider()).run(workflow_state)

    assert 1 <= len(workflow_state.plan) <= 4
    assert workflow_state.plan_details
    assert workflow_state.learning_context["preferred_resources"] == workflow_state.plan_details
    assert workflow_state.plan[0] in {"lecture_doc", "mind_map", "visual_card", "animation_demo", "quiz"}
    assert any(item["reason"] for item in workflow_state.plan_details)
    assert "预计学习" in result["summary"]


def test_orchestrator_respects_planner_selected_resources():
    profile = state.Profile(
        mastery=0.24,
        preferred_modalities=["图解"],
        time_budget="每天 20 分钟",
        weak_points=["概念混淆"],
        mistake_patterns=["术语混淆"],
        updated_at=state.now(),
    )
    request = state.GenerateRequest(
        chapter="机器学习基础",
        goal="先弄懂核心概念",
        pain_points=["概念混淆"],
    )

    final_state = None
    for _agent, workflow_state in Orchestrator().generate("job_planner_orchestrator_test", request, profile):
        final_state = workflow_state

    assert final_state is not None
    assert final_state.plan
    assert {resource.type for resource in final_state.resources} == set(final_state.plan)
    assert len(final_state.resources) <= 4


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
    assert all("retrieval_channels" in item for item in workflow_state.sources)
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


def test_current_learning_path_repairs_stale_resource_references():
    original_profile = state.profile
    original_resources = state.resources
    original_path = state.learning_path
    original_assessment = state.assessment_report
    try:
        state.profile = state.Profile(updated_at=state.now())
        state.resources = [
            Resource(
                id="res_current",
                type="lecture_doc",
                title="Current resource",
                content_format="markdown",
                content="Demo content",
                source_refs=["demo#objectives"],
                difficulty="入门",
                target_profile=["demo"],
                review_status="passed",
                created_by_agents=["TestAgent"],
                created_at=state.now(),
            )
        ]
        state.learning_path = state.LearningPath(
            id="path_stale",
            profile_version=1,
            mastery=0.2,
            adjustment_reason="stale path",
            updated_at=state.now(),
            steps=[
                state.LearningPathStep(
                    id="step_01",
                    title="Stale",
                    objective="References an old resource",
                    recommended_resource_ids=["res_missing"],
                    reason="stale",
                    estimated_minutes=10,
                )
            ],
        )
        state.assessment_report = None

        repaired = payload(client.get("/api/learning-path/current"))
        valid_ids = {resource.id for resource in state.resources}
        referenced_ids = [
            resource_id
            for step in repaired["steps"]
            for resource_id in step["recommended_resource_ids"]
        ]

        assert referenced_ids
        assert all(resource_id in valid_ids for resource_id in referenced_ids)
    finally:
        state.profile = original_profile
        state.resources = original_resources
        state.learning_path = original_path
        state.assessment_report = original_assessment


def test_api_contract_endpoints_return_documented_shapes():
    health = payload(client.get("/api/health"))
    assert_fields(health, {"status", "mock_llm", "course", "vector_store"})
    assert health["llm_provider"] == "mock"
    assert_fields(health["vector_store"], {"requested", "active", "fallback", "collection"})

    profile = payload(client.get("/api/profile/current"))
    assert_fields(profile, PROFILE_FIELDS)

    profile_chat = payload(client.post("/api/profile/chat", json={"message": "Python"}))
    assert_fields(profile_chat, {"profile", "extracted", "suggested_next_question", "version_change", "fusion_meta", "changed_fields"})
    assert_fields(profile_chat["profile"], PROFILE_FIELDS)

    versions = payload(client.get("/api/profile/versions"))
    assert isinstance(versions, list)
    assert versions
    assert_fields(versions[0], PROFILE_FIELDS)
    rollback = payload(client.post(f"/api/profile/rollback/{profile_chat['profile']['version']}"))
    assert_fields(rollback, {"profile", "learning_path"})
    assert_fields(rollback["profile"], PROFILE_FIELDS)

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

    history = payload(client.get("/api/resources/history"))
    assert isinstance(history, list)
    assert history
    history_summary = next(item for item in history if item["id"] == job["id"])
    assert_fields(history_summary, HISTORY_SUMMARY_FIELDS)
    assert "resources" not in history_summary
    assert "traces" not in history_summary
    assert "events" not in history_summary
    assert history_summary["resource_count"] == len(job["resources"])
    assert history_summary["resource_type_counts"]

    history_detail = payload(client.get(f"/api/resources/history/{job['id']}"))
    assert_fields(history_detail, JOB_FIELDS | {"is_current"})
    assert history_detail["id"] == job["id"]
    assert history_detail["resources"]
    assert isinstance(history_detail["traces"], list)
    assert isinstance(history_detail["events"], list)

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

    tutor = payload(client.post("/api/tutor/chat", json={
        "question": "What is overfitting?",
        "resource_id": None,
        "history": [
            {"role": "user", "content": "我不太理解训练集和测试集"},
            {"role": "assistant", "content": "可以把训练集看成课堂练习。"},
        ],
    }))
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

    history_job_error = error_payload(client.get("/api/resources/history/not_found"), 404)
    assert history_job_error["code"] == "JOB_NOT_FOUND"
    assert history_job_error["message"] == "history job not found"

    resource_error = error_payload(client.get("/api/resources/not_found"), 404)
    assert resource_error["code"] == "RESOURCE_NOT_FOUND"
    assert resource_error["message"] == "resource not found"

    validation_error = error_payload(client.post("/api/profile/chat", json={}), 422)
    assert validation_error["code"] == "VALIDATION_ERROR"

    empty_message_error = error_payload(client.post("/api/profile/chat", json={"message": ""}), 422)
    assert empty_message_error["code"] == "VALIDATION_ERROR"

    empty_quiz_error = error_payload(client.post("/api/quiz/submit", json={"answers": []}), 422)
    assert empty_quiz_error["code"] == "VALIDATION_ERROR"


def test_hydrate_from_db_restores_persisted_demo_state(monkeypatch, tmp_path):
    original_profile = state.profile
    original_jobs = state.jobs
    original_resources = state.resources
    original_path = state.learning_path
    original_assessment = state.assessment_report

    test_db = tmp_path / f"test_app_hydrate_{uuid4().hex}.db"
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


def test_cache_is_optional_when_redis_url_is_missing(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    cache.reset_cache_client()

    assert cache.status()["enabled"] is False
    assert cache.cache_json("job", "job_disabled_cache", {"ok": True}) is False

    health = payload(client.get("/api/health"))
    assert health["cache"]["enabled"] is False
    assert health["cache"]["available"] is False


def test_job_endpoint_recovers_job_snapshot_from_redis_cache(monkeypatch):
    class FakeRedis:
        def __init__(self, payload: dict):
            self.payload = payload

        def get(self, key: str):
            assert key == "a3:job:job_cached_snapshot"
            return json.dumps(self.payload, ensure_ascii=False)

    original_jobs = state.jobs
    job = state.GenerationJob(
        id="job_cached_snapshot",
        status="completed",
        progress=100,
        current_step="job_completed",
        request=state.GenerateRequest(chapter="鏈哄櫒瀛︿範鍩虹", goal="cache recovery"),
        created_at=state.now(),
        completed_at=state.now(),
    )
    monkeypatch.setattr(cache, "_redis_client", lambda: FakeRedis(job.model_dump()))
    try:
        state.jobs = {}
        data = payload(client.get("/api/jobs/job_cached_snapshot"))

        assert data["id"] == "job_cached_snapshot"
        assert data["status"] == "completed"
        assert state.jobs["job_cached_snapshot"].progress == 100
    finally:
        state.jobs = original_jobs


def test_review_agent_attempts_real_llm_fact_check():
    llm = ReviewFactCheckLLM()
    agent = ReviewAgent(llm)
    chapter = COURSE["chapters"][3]

    result = agent._attempt_llm_fact_check("这段内容包含一个需要复核的机器学习事实。", chapter)

    assert llm.calls == 1
    assert result is not None
    assert result["is_accurate"] is False
    assert result["confidence"] == 0.88


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
                f"训练集用于学习规律，泛化关注新数据表现。[来源: {chapter_id}#detailed_concepts:01] "
                f"损失函数用于衡量预测差距，过拟合会导致测试表现下降。[来源: {chapter_id}#misconceptions:01] "
                "需要结合机器学习基础中的方法适用条件、概念边界和案例分析。"
            ),
            evidence_sources=[
                {
                    "id": f"{chapter_id}#detailed_concepts:01",
                    "text": "训练集、泛化、损失函数和过拟合是机器学习基础中的关键概念。",
                    "relevance_score": 0.93,
                    "reason": "覆盖核心概念。",
                },
                {
                    "id": f"{chapter_id}#misconceptions:01",
                    "text": "过拟合会导致训练表现好但新数据表现下降。",
                    "relevance_score": 0.91,
                    "reason": "覆盖常见误区。",
                },
            ],
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
            evidence_sources=[
                {
                    "id": f"{chapter_id}#not_exist:01",
                    "text": "训练集和泛化是机器学习基础中的概念。",
                    "relevance_score": 0.3,
                    "reason": "非法测试来源。",
                }
            ],
            difficulty="入门",
            target_profile=["练习"],
            review_status="needs_revision",
            created_by_agents=["QuizAgent"],
            created_at=state.now(),
        ),
        Resource(
            id="res_missing_evidence_text",
            type="lecture_doc",
            title="缺少证据原文",
            content_format="markdown",
            content=f"训练集和泛化相关。[来源: {chapter_id}#detailed_concepts:02]",
            evidence_sources=[
                {
                    "id": f"{chapter_id}#detailed_concepts:02",
                    "text": "",
                    "relevance_score": 0.8,
                    "reason": "缺少原文测试。",
                }
            ],
            difficulty="入门",
            target_profile=["例子驱动"],
            review_status="needs_revision",
            created_by_agents=["LectureAgent"],
            created_at=state.now(),
        ),
        Resource(
            id="res_unknown_inline_ref",
            type="lecture_doc",
            title="错误正文引用",
            content_format="markdown",
            content=f"训练集和泛化相关。[来源: {chapter_id}#detailed_concepts:99]",
            evidence_sources=[
                {
                    "id": f"{chapter_id}#detailed_concepts:03",
                    "text": "训练集和泛化是机器学习基础中的核心概念。",
                    "relevance_score": 0.8,
                    "reason": "用于测试正文引用映射。",
                }
            ],
            difficulty="入门",
            target_profile=["例子驱动"],
            review_status="needs_revision",
            created_by_agents=["LectureAgent"],
            created_at=state.now(),
        ),
        Resource(
            id="res_unsupported_inline_context",
            type="lecture_doc",
            title="引用附近缺少证据支撑",
            content_format="markdown",
            content=(
                "训练集、泛化、过拟合属于机器学习基础，学习时需要区分训练表现和测试表现。"
                "下面这段故意偏离证据：火星矿石会自动预测彩票号码，并且可以让所有模型无需数据就得到满分。"
                "这种说法和课程证据没有可验证关系，只是为了测试引用窗口。"
                f"[来源: {chapter_id}#detailed_concepts:01]"
            ),
            evidence_sources=[
                {
                    "id": f"{chapter_id}#detailed_concepts:01",
                    "text": "训练集、泛化、损失函数和过拟合是机器学习基础中的关键概念。",
                    "relevance_score": 0.93,
                    "reason": "覆盖核心概念。",
                }
            ],
            difficulty="入门",
            target_profile=["例子驱动"],
            review_status="needs_revision",
            created_by_agents=["LectureAgent"],
            created_at=state.now(),
        ),
        Resource(
            id="res_blocked",
            type="lecture_doc",
            title="风险内容",
            content_format="markdown",
            content=f"训练集 泛化 违法 内容 [来源: {chapter_id}#detailed_concepts:01]",
            evidence_sources=[
                {
                    "id": f"{chapter_id}#detailed_concepts:01",
                    "text": "训练集和泛化是机器学习基础中的概念。",
                    "relevance_score": 0.8,
                    "reason": "风险测试来源。",
                }
            ],
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
    assert "缺少 evidence_sources" in resources["res_missing_source"].audit_reason

    assert resources["res_invalid_source"].review_status == "needs_revision"
    assert "无效证据来源" in "；".join(resources["res_invalid_source"].review_notes)

    assert resources["res_missing_evidence_text"].review_status == "needs_revision"
    assert "缺少证据原文" in "；".join(resources["res_missing_evidence_text"].review_notes)

    assert resources["res_unknown_inline_ref"].review_status == "needs_revision"
    assert "无法映射的正文引用" in "；".join(resources["res_unknown_inline_ref"].review_notes)

    assert resources["res_unsupported_inline_context"].review_status == "needs_revision"
    assert "引用附近缺少对应证据支撑" in "；".join(resources["res_unsupported_inline_context"].review_notes)

    assert resources["res_blocked"].review_status == "blocked"
    assert resources["res_blocked"].review_confidence == 0.35
    assert "blocked=1" in result["summary"]

from app.knowledge import match_chapter
from app.schemas import GenerateRequest, Profile
from app.state import resolve_generation_request


def test_match_supervised_learning_from_user_need():
    result = match_chapter("帮我生成监督学习分类和回归的练习")

    assert result["chapter"]["title"] == "监督学习"
    assert result["confidence"] >= 0.7


def test_match_nlp_from_user_need():
    result = match_chapter("我想要 NLP 分词和词向量讲解")

    assert result["chapter"]["title"] == "自然语言处理"
    assert result["confidence"] >= 0.7


def test_match_reinforcement_learning_from_user_need():
    result = match_chapter("强化学习奖励和策略不懂")

    assert result["chapter"]["title"] == "强化学习"
    assert result["confidence"] >= 0.7


def test_match_expert_system_from_user_need():
    result = match_chapter("专家系统的推理机和知识库怎么配合")

    assert result["chapter"]["title"] == "专家系统"
    assert result["confidence"] >= 0.7


def test_match_rag_from_user_need():
    result = match_chapter("RAG Top-K 和重排序怎么影响知识库问答")

    assert result["chapter"]["title"] == "大语言模型与知识库问答"
    assert result["confidence"] >= 0.7


def test_resolve_generation_uses_profile_chapter_when_prompt_is_ambiguous():
    profile = Profile(current_chapter="专家系统", learning_goal="掌握推理机")
    request = GenerateRequest(goal="帮我生成一套练习", raw_user_need="帮我生成一套练习")

    resolved, warnings = resolve_generation_request(request, profile)

    assert resolved.chapter == "专家系统"
    assert resolved.chapter_match_confidence >= 0.5
    assert warnings


def test_resolve_generation_records_default_warning_when_no_context():
    request = GenerateRequest(goal="帮我生成一份学习资源", raw_user_need="帮我生成一份学习资源")

    resolved, warnings = resolve_generation_request(request, Profile())

    assert resolved.chapter == "人工智能概述"
    assert resolved.chapter_match_confidence <= 0.3
    assert any("默认章节" in warning or "当前使用" in warning for warning in warnings)


def test_resolve_generation_infers_requested_resource_types_from_prompt():
    request = GenerateRequest(
        goal="为监督学习和过拟合生成讲解，导图，练习题",
        raw_user_need="为监督学习和过拟合生成讲解，导图，练习题",
    )

    resolved, _warnings = resolve_generation_request(request, Profile())

    assert resolved.chapter == "监督学习"
    assert resolved.resource_types == ["lecture_doc", "mind_map", "quiz"]

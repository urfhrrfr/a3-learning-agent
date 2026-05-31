import os

os.environ.setdefault("LLM_PROVIDER", "mock")

from app.knowledge import COURSE
from app.embedding import MockEmbeddingProvider
from app.retrieval import HybridRetriever, VectorRetriever, build_course_chunks, build_course_vector_index
from app.vector_store import MemoryVectorStore, VectorRecord, get_vector_store, vector_store_status


def test_course_chunks_are_structured_and_traceable():
    chunks = build_course_chunks(COURSE)

    assert len(chunks) >= 120
    first = chunks[0]
    assert first.id.startswith("ai_intro/ch")
    assert first.course_id == "ai_intro"
    assert first.chapter_id
    assert first.chapter_title
    assert first.section
    assert first.section_label
    assert first.text
    assert first.keywords

    source = first.as_source(0.9, "test")
    assert source["id"] == first.id
    assert source["text"] == first.text
    assert source["relevance_score"] == 0.9
    assert source["reason"] == "test"


def test_hybrid_retriever_prioritizes_chapter_profile_and_resource_type():
    retriever = HybridRetriever(COURSE, max_candidates=12, top_k=5)

    selected, warnings = retriever.retrieve(
        query="机器学习基础；学习目标：理解泛化与过拟合；当前困惑：公式迁移",
        profile_context="学习目标：完成课程项目\n薄弱点：过拟合\n偏好：代码案例",
        current_chapter_id="ai_intro/ch07",
        preferred_sections={"code_labs", "misconceptions", "detailed_concepts"},
    )

    assert warnings == []
    assert selected
    assert all(item["id"].startswith("ai_intro/ch") for item in selected)
    assert any(item["chapter_title"] == COURSE["chapters"][6]["title"] for item in selected)
    assert any(item["section"] in {"code_labs", "misconceptions", "detailed_concepts"} for item in selected)
    assert all(item["text"] for item in selected)
    assert all(0 <= item["relevance_score"] <= 1 for item in selected)
    assert all("vector" in item["retrieval_channels"] for item in selected)
    assert all({"lexical_score", "vector_score", "profile_boost", "final_score", "retrieval_channels"} <= set(item) for item in selected)


def test_hybrid_retriever_merges_lexical_and_vector_channels_for_same_query():
    retriever = HybridRetriever(COURSE, max_candidates=20, top_k=8)

    selected, warnings = retriever.retrieve(
        query="overfitting generalization training set test set",
        profile_context="weak points: overfitting; mistake pattern: confused train and test performance",
        current_chapter_id="ai_intro/ch07",
        preferred_sections={"misconceptions", "detailed_concepts", "practice_questions"},
    )

    assert warnings == []
    assert selected
    assert any({"lexical", "vector"} <= set(item["retrieval_channels"]) for item in selected)
    assert all(item["final_score"] >= item["profile_boost"] for item in selected)


def test_hybrid_rerank_prompt_includes_channel_scores():
    retriever = HybridRetriever(COURSE, max_candidates=12, top_k=5)
    lexical_candidates = retriever.lexical.retrieve(
        "overfitting generalization",
        "weak points: overfitting",
        "ai_intro/ch07",
        preferred_sections={"misconceptions"},
        max_candidates=8,
    )
    vector_candidates = retriever.vector.retrieve_candidates(
        query="overfitting generalization",
        profile_context="weak points: overfitting",
        current_chapter_id="ai_intro/ch07",
        preferred_sections={"misconceptions"},
        max_candidates=8,
    )
    candidates = retriever.merge_candidates(
        lexical_candidates,
        vector_candidates,
        current_chapter_id="ai_intro/ch07",
        preferred_sections={"misconceptions"},
    )

    prompt = retriever.build_rerank_prompt("overfitting generalization", "weak points: overfitting", candidates)

    assert "lexical=" in prompt
    assert "vector=" in prompt
    assert "final=" in prompt
    assert "channels=" in prompt


def test_mock_embedding_dimension_is_stable():
    embedding = MockEmbeddingProvider()

    first = embedding.embed_text("machine learning overfitting")
    second = embedding.embed_text("machine learning overfitting")

    assert len(first) == embedding.dimension
    assert first == second
    assert len(embedding.embed_text("")) == embedding.dimension


def test_memory_vector_store_can_upsert_and_search():
    store = MemoryVectorStore()
    store.upsert(
        [
            VectorRecord(id="a", vector=[1.0, 0.0], document="alpha", metadata={"chapter_id": "ch1"}),
            VectorRecord(id="b", vector=[0.0, 1.0], document="beta", metadata={"chapter_id": "ch2"}),
        ]
    )

    results = store.search([1.0, 0.0], top_k=1)
    filtered = store.search([1.0, 0.0], top_k=2, metadata_filter={"chapter_id": "ch2"})

    assert results[0].record.id == "a"
    assert results[0].score == 1.0
    assert [item.record.id for item in filtered] == ["b"]


def test_vector_store_factory_defaults_to_memory(monkeypatch):
    monkeypatch.delenv("VECTOR_STORE", raising=False)
    monkeypatch.delenv("VECTOR_STORE_PROVIDER", raising=False)

    assert isinstance(get_vector_store(collection_name="ai_intro"), MemoryVectorStore)


def test_vector_store_factory_falls_back_when_chroma_unavailable(monkeypatch):
    monkeypatch.setenv("VECTOR_STORE", "chroma")
    monkeypatch.setitem(__import__("sys").modules, "chromadb", None)

    store = get_vector_store(collection_name="ai_intro")
    status = vector_store_status(collection_name="ai_intro")

    assert isinstance(store, MemoryVectorStore)
    assert status["requested"] == "chroma"
    assert status["active"] == "memory"
    assert status["fallback"] is True


def test_indexer_builds_course_vector_index():
    index = build_course_vector_index(COURSE, embedding=MockEmbeddingProvider(), store=MemoryVectorStore())

    assert len(index.chunks) >= 120
    assert len(index.store.records) == len(index.chunks)
    first = index.chunks[0]
    assert first.id in index.chunks_by_id
    assert index.store.records[first.id].metadata["chapter_id"] == first.chapter_id


def test_vector_retriever_returns_evidence_sources():
    retriever = VectorRetriever(COURSE, embedding=MockEmbeddingProvider(), store=MemoryVectorStore(), top_k=5)

    selected = retriever.retrieve(
        query="overfitting and generalization",
        profile_context="weak points: overfitting; prefers code cases",
        current_chapter_id="ai_intro/ch07",
        preferred_sections={"misconceptions", "detailed_concepts", "code_labs"},
    )

    assert selected
    assert all(item["id"].startswith("ai_intro/ch") for item in selected)
    assert all(item["text"] for item in selected)
    assert all("relevance_score" in item for item in selected)
    assert all("reason" in item for item in selected)
    assert all("vector" in item["retrieval_channels"] for item in selected)


def test_new_knowledge_base_queries_retrieve_expected_chapters():
    retriever = HybridRetriever(COURSE, max_candidates=20, top_k=5)

    scenarios = [
        ("A* 和贪婪搜索区别", "搜索算法", "ai_intro/ch03"),
        ("过拟合怎么解决", "机器学习基础", "ai_intro/ch07"),
        ("Transformer 的 QKV 自注意力", "神经网络与深度学习", "ai_intro/ch11"),
        ("RAG 为什么能减少幻觉", "大语言模型与知识库问答", "ai_intro/ch13"),
    ]

    for query, expected_title, chapter_id in scenarios:
        selected, warnings = retriever.retrieve(
            query=query,
            profile_context="",
            current_chapter_id=chapter_id,
            preferred_sections={"detailed_concepts", "concept_cards", "misconceptions"},
        )

        assert warnings == []
        assert selected
        assert any(item["chapter_title"] == expected_title for item in selected)

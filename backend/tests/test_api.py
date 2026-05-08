from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def payload(response):
    body = response.json()
    assert body["ok"] is True
    return body["data"]


def test_profile_chat_updates_profile():
    data = payload(client.post("/api/profile/chat", json={"message": "我线性代数薄弱，希望多给 Python 代码案例"}))
    assert data["profile"]["version"] >= 2
    assert "代码案例" in data["profile"]["preferred_modalities"]


def test_generation_returns_resources_and_trace():
    data = payload(
        client.post(
            "/api/resources/generate",
            json={"course": "人工智能导论", "chapter": "机器学习基础", "goal": "理解泛化与过拟合", "pain_points": ["公式迁移"]},
        )
    )
    assert data["status"] == "completed"
    assert len(data["resources"]) >= 6
    assert len(data["traces"]) >= 8
    assert all(item["source_refs"] for item in data["resources"])


def test_quiz_submit_creates_assessment_and_path():
    data = payload(client.post("/api/quiz/submit", json={"answers": ["过拟合会导致泛化下降"], "resource_id": None}))
    assert data["score"] >= 80
    assert data["adjusted_path"]["steps"]

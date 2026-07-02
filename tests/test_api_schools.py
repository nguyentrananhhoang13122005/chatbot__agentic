from fastapi.testclient import TestClient
from main import app
import pytest

client = TestClient(app)

def test_match_schools_endpoint():
    payload = {
        "scores": {
            "Toán": 8.5,
            "Vật lý": 9.0,
            "Hóa học": 8.0
        },
        "bonus": 0.0,
        "methods": ["Xét điểm thi THPT"],
        "k": 3,
        "stream": False
    }
    response = client.post("/api/v1/schools/match", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "schools" in data
    assert "top_combinations" in data
    assert "analysis" in data
    assert isinstance(data["schools"], list)
    assert len(data["schools"]) > 0

def test_recommend_schools_endpoint():
    payload = {
        "user_query": "Điểm chuẩn trường đại học bách khoa hà nội ngành CNTT",
        "stream": False
    }
    response = client.post("/api/v1/schools/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert len(data["answer"]) > 0

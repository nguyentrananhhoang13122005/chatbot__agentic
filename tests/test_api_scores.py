from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_calculate_scores_api():
    payload = {
        "scores": {
            "Toán": 8.5,
            "Vật lý": 9.0,
            "Hóa học": 8.0
        },
        "bonus": 0.5,
        "k": 3
    }
    
    response = client.post("/api/v1/scores/calculate", json=payload)
    
    assert response.status_code == 200, response.text
    data = response.json()
    
    assert "top_combinations" in data
    assert "analysis" in data
    
    combos = data["top_combinations"]
    assert len(combos) > 0
    # Khối A00 (Toán, Lý, Hóa) phải có mặt
    assert any(c["code"] == "A00" for c in combos)
    
    # Kiểm tra tổng điểm A00 (có giảm trừ điểm ưu tiên theo luật >=22.5)
    a00 = next(c for c in combos if c["code"] == "A00")
    assert abs(a00["total"] - 25.8) < 0.01

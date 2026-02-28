from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_full_pipeline():
    response = client.post("/api/v1/research/query", json={"query": "Generative AI in healthcare"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "report" in data
    print("Full pipeline test successful. Report keys:", data["report"].keys())

    # Test history
    history_res = client.get("/api/v1/research/history")
    assert history_res.status_code == 200
    print("History test successful. Count:", len(history_res.json()["history"]))

if __name__ == "__main__":
    test_full_pipeline()

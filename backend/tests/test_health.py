from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_reaches_database():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}

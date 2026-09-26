from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_comparison_returns_all_five_paradigms_and_a_real_count():
    response = client.get("/comparison-view/duplicate-delivery")
    assert response.status_code == 200
    body = response.json()
    assert len(body["entries"]) == 5
    paradigms = {e["paradigm"] for e in body["entries"]}
    assert len(paradigms) == 5  # no duplicate/placeholder entries
    for entry in body["entries"]:
        assert entry["code"].strip()
        assert entry["explanation"].strip()
    assert body["real_duplicate_count"] > 0

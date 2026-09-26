from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_learn_page_aggregates_every_phases_real_remediation_content():
    response = client.get("/learn-page")
    assert response.status_code == 200
    body = response.json()

    assert body["overview"].strip()
    assert len(body["phases"]) == 5

    for phase in body["phases"]:
        assert phase["phase"].strip()
        assert phase["one_liner"].strip()
        assert len(phase["entries"]) > 0
        for entry in phase["entries"]:
            assert entry["error_code"].startswith("ERR_")
            assert entry["why"].strip()
            assert entry["fix"].strip()
            assert entry["tradeoffs"].strip()

    assert len(body["comparison"]["entries"]) == 5

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_task_endpoint_returns_content():
    response = client.get("/postgres-phase/task")
    assert response.status_code == 200
    assert "source_table" in response.json()


def test_full_session_lifecycle():
    create = client.post("/postgres-phase/sessions")
    assert create.status_code == 200
    session_id = create.json()["session_id"]

    create_table = client.post(
        f"/postgres-phase/sessions/{session_id}/execute",
        json={"sql": "CREATE TABLE t (id int)"},
    )
    assert create_table.status_code == 200
    assert create_table.json()["success"] is True

    query = client.post(
        f"/postgres-phase/sessions/{session_id}/execute",
        json={"sql": "SELECT COUNT(*) FROM public.raw_transaction_events"},
    )
    assert query.json()["success"] is True
    assert query.json()["columns"] == ["count"]

    blocked = client.post(
        f"/postgres-phase/sessions/{session_id}/execute",
        json={"sql": "SELECT * FROM public.injected_fault_log"},
    )
    assert blocked.json()["success"] is False
    assert blocked.json()["error_code"] == "42501"

    bad_sql = client.post(
        f"/postgres-phase/sessions/{session_id}/execute",
        json={"sql": "SELECT * FROM nonexistent_table"},
    )
    assert bad_sql.status_code == 200  # never a 500, even for bad user SQL
    assert bad_sql.json()["success"] is False

    end = client.delete(f"/postgres-phase/sessions/{session_id}")
    assert end.status_code == 200

    after_end = client.post(
        f"/postgres-phase/sessions/{session_id}/execute",
        json={"sql": "SELECT 1"},
    )
    assert after_end.status_code == 404


def test_execute_on_unknown_session_returns_404():
    response = client.post(
        "/postgres-phase/sessions/does-not-exist/execute",
        json={"sql": "SELECT 1"},
    )
    assert response.status_code == 404

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_interview_questions_returns_every_topic_with_real_content():
    response = client.get("/interview-questions")
    assert response.status_code == 200
    body = response.json()

    topics = body["topics"]
    assert len(topics) >= 5

    seen_questions = set()
    seen_prompts = set()
    for topic in topics:
        assert topic["topic"].strip()
        assert len(topic["questions"]) >= 4
        for item in topic["questions"]:
            assert item["q"].strip().endswith("?")
            assert len(item["a"].strip()) > 40
            assert item["q"] not in seen_questions
            seen_questions.add(item["q"])

        assert len(topic["coding"]) >= 3
        for item in topic["coding"]:
            assert item["prompt"].strip()
            assert item["solution"].strip()
            assert len(item["note"].strip()) > 20
            assert item["prompt"] not in seen_prompts
            seen_prompts.add(item["prompt"])

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_ai_decision_endpoint_generates_decision():
    response = client.post(
        "/recovery-cases/pay_test_001"
    )

    assert response.status_code == 200

    case = response.json()
    case_id = case["case_id"]

    response = client.post(
        f"/recovery-cases/{case_id}/ai-decision"
    )

    assert response.status_code == 200

    decision = response.json()

    assert decision["case_id"] == case_id
    assert decision["recommended_action"] in {
        "retry_payment",
        "manual_review",
    }
    assert decision["confidence"] in {
        "low",
        "medium",
        "high",
    }
    assert decision["rationale"]
    assert decision["created_at"]

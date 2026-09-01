from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_ai_action_endpoint_generates_action():
    response = client.post(
        "/recovery-cases/pay_test_001"
    )

    assert response.status_code == 200

    case = response.json()
    case_id = case["case_id"]

    response = client.post(
        f"/recovery-cases/{case_id}/ai-action"
    )

    assert response.status_code == 200

    action = response.json()

    assert action["action_id"].startswith("action_")
    assert action["case_id"] == case_id
    assert action["action_type"] in {
        "retry_payment",
        "send_reminder",
        "update_payment_method",
        "offer_alternative_method",
        "escalate",
    }
    assert action["status"] == "proposed"
    assert action["proposed_at"]


def test_ai_action_endpoint_missing_case_returns_404():
    response = client.post(
        "/recovery-cases/case_does_not_exist/ai-action"
    )

    assert response.status_code == 404
    assert "Recovery case not found" in response.json()["detail"]

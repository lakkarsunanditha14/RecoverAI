from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_record_recovered_outcome():
    response = client.post(
        "/recovery-cases/pay_test_001"
    )

    assert response.status_code == 200

    case = response.json()
    case_id = case["case_id"]

    action_response = client.post(
        f"/recovery-cases/{case_id}/ai-action"
    )

    assert action_response.status_code == 200

    action = action_response.json()
    action_id = action["action_id"]

    outcome_response = client.post(
        f"/recovery-cases/{case_id}/outcomes",
        json={
            "action_id": action_id,
            "status": "recovered",
            "amount_recovered": "4999.00",
        },
    )

    assert outcome_response.status_code == 200

    outcome = outcome_response.json()

    assert outcome["outcome_id"].startswith("outcome_")
    assert outcome["case_id"] == case_id
    assert outcome["action_id"] == action_id
    assert outcome["status"] == "recovered"
    assert Decimal(outcome["amount_recovered"]) == Decimal("4999.00")
    assert outcome["recorded_at"]


def test_record_outcome_with_missing_action_returns_404():
    response = client.post(
        "/recovery-cases/pay_test_001"
    )

    assert response.status_code == 200

    case = response.json()
    case_id = case["case_id"]

    response = client.post(
        f"/recovery-cases/{case_id}/outcomes",
        json={
            "action_id": "action_does_not_exist",
            "status": "recovered",
            "amount_recovered": "4999.00",
        },
    )

    assert response.status_code == 404
    assert "Recovery action not found" in response.json()["detail"]


def test_record_outcome_for_missing_case_returns_404():
    response = client.post(
        "/recovery-cases/case_does_not_exist/outcomes",
        json={
            "action_id": "action_does_not_exist",
            "status": "recovered",
            "amount_recovered": "4999.00",
        },
    )

    assert response.status_code == 404
    assert "Recovery case not found" in response.json()["detail"]

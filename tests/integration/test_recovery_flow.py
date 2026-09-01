from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_complete_recovery_flow():
    # 1. Create recovery case
    response = client.post("/recovery-cases/pay_test_001")

    assert response.status_code == 200

    case = response.json()

    assert case["payment_id"] == "pay_test_001"
    assert case["customer_id"] == "cust_test_001"
    assert case["amount_at_risk"] == "4999.00"
    assert case["status"] == "created"

    case_id = case["case_id"]

    # 2. Create recovery decision
    response = client.post(
        f"/recovery-cases/{case_id}/decisions",
        json={
            "recommended_action": "retry_payment",
            "confidence": "high",
            "rationale": (
                "Payment failed for the customer; "
                "retrying the payment is the initial recovery action."
            ),
        },
    )

    assert response.status_code == 200

    decision = response.json()

    assert decision["case_id"] == case_id
    assert decision["recommended_action"] == "retry_payment"
    assert decision["confidence"] == "high"

    # 3. Propose recovery action
    response = client.post(
        f"/recovery-cases/{case_id}/actions",
        json={
            "action_type": "retry_payment",
        },
    )

    assert response.status_code == 200

    action = response.json()

    assert action["case_id"] == case_id
    assert action["action_type"] == "retry_payment"
    assert action["status"] == "proposed"

    action_id = action["action_id"]

    # 4. Record recovery outcome
    response = client.post(
        f"/recovery-cases/{case_id}/outcomes",
        json={
            "action_id": action_id,
            "status": "recovered",
            "amount_recovered": "4999.00",
        },
    )

    assert response.status_code == 200

    outcome = response.json()

    assert outcome["case_id"] == case_id
    assert outcome["action_id"] == action_id
    assert outcome["status"] == "recovered"
    assert outcome["amount_recovered"] == "4999.00"

    # 5. Record audit event
    response = client.post(
        f"/recovery-cases/{case_id}/audit-events",
        json={
            "event_type": "recovery_completed",
            "actor": "system",
            "reason": (
                "Payment recovery completed successfully "
                "after the retry action."
            ),
        },
    )

    assert response.status_code == 200

    event = response.json()

    assert event["case_id"] == case_id
    assert event["event_type"] == "recovery_completed"
    assert event["actor"] == "system"
    assert event["reason"] == (
        "Payment recovery completed successfully "
        "after the retry action."
    )

def test_failed_recovery_flow():
    # 1. Create recovery case
    response = client.post("/recovery-cases/pay_test_001")

    assert response.status_code == 200

    case = response.json()
    case_id = case["case_id"]

    # 2. Propose recovery action
    response = client.post(
        f"/recovery-cases/{case_id}/actions",
        json={
            "action_type": "retry_payment",
        },
    )

    assert response.status_code == 200

    action = response.json()

    assert action["case_id"] == case_id
    assert action["action_type"] == "retry_payment"
    assert action["status"] == "proposed"

    action_id = action["action_id"]

    # 3. Record failed recovery outcome
    response = client.post(
        f"/recovery-cases/{case_id}/outcomes",
        json={
            "action_id": action_id,
            "status": "not_recovered",
            "amount_recovered": "0.00",
        },
    )

    assert response.status_code == 200

    outcome = response.json()

    assert outcome["case_id"] == case_id
    assert outcome["action_id"] == action_id
    assert outcome["status"] == "not_recovered"
    assert outcome["amount_recovered"] == "0.00"


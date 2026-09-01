from time import sleep

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def create_case():
    response = client.post(
        "/recovery-cases/pay_test_001"
    )

    assert response.status_code == 200

    return response.json()["case_id"]


def test_get_audit_events_for_case():
    case_id = create_case()

    first_response = client.post(
        f"/recovery-cases/{case_id}/audit-events",
        json={
            "event_type": "payment_failed",
            "actor": "system",
            "reason": "Payment attempt failed.",
        },
    )

    assert first_response.status_code == 200

    sleep(0.01)

    second_response = client.post(
        f"/recovery-cases/{case_id}/audit-events",
        json={
            "event_type": "risk_assessed",
            "actor": "risk_engine",
            "reason": "Recovery risk assessment completed.",
        },
    )

    assert second_response.status_code == 200

    response = client.get(
        f"/recovery-cases/{case_id}/audit-events"
    )

    assert response.status_code == 200

    events = response.json()

    assert len(events) == 2

    assert events[0]["case_id"] == case_id
    assert events[0]["event_type"] == "payment_failed"
    assert events[0]["actor"] == "system"

    assert events[1]["case_id"] == case_id
    assert events[1]["event_type"] == "risk_assessed"
    assert events[1]["actor"] == "risk_engine"


def test_get_audit_events_for_missing_case_returns_404():
    response = client.get(
        "/recovery-cases/case_does_not_exist/audit-events"
    )

    assert response.status_code == 404
    assert "Recovery case not found" in response.json()["detail"]

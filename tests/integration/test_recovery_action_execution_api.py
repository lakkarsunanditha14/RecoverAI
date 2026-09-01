from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def create_action():
    response = client.post(
        "/recovery-cases/pay_test_001"
    )

    assert response.status_code == 200

    case_id = response.json()["case_id"]

    response = client.post(
        f"/recovery-cases/{case_id}/ai-action"
    )

    assert response.status_code == 200

    return response.json()


def test_action_execution_lifecycle():
    action = create_action()
    action_id = action["action_id"]

    assert action["status"] == "proposed"

    response = client.post(
        f"/recovery-actions/{action_id}/approve"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"

    response = client.post(
        f"/recovery-actions/{action_id}/start"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "executing"

    response = client.post(
        f"/recovery-actions/{action_id}/complete"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_action_execution_can_fail():
    action = create_action()
    action_id = action["action_id"]

    response = client.post(
        f"/recovery-actions/{action_id}/approve"
    )

    assert response.status_code == 200

    response = client.post(
        f"/recovery-actions/{action_id}/start"
    )

    assert response.status_code == 200

    response = client.post(
        f"/recovery-actions/{action_id}/fail"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "failed"


def test_missing_action_returns_404():
    response = client.post(
        "/recovery-actions/action_does_not_exist/approve"
    )

    assert response.status_code == 404
    assert "Recovery action not found" in response.json()["detail"]


def test_invalid_transition_returns_404():
    action = create_action()
    action_id = action["action_id"]

    response = client.post(
        f"/recovery-actions/{action_id}/complete"
    )

    assert response.status_code == 404
    assert "cannot be completed" in response.json()["detail"]

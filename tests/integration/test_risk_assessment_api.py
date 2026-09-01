from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_create_risk_assessment():
    # 1. Create recovery case
    response = client.post("/recovery-cases/pay_test_001")

    assert response.status_code == 200

    case = response.json()
    case_id = case["case_id"]

    # 2. Create risk assessment
    response = client.post(
        f"/recovery-cases/{case_id}/risk-assessments"
    )

    assert response.status_code == 200

    assessment = response.json()

    assert assessment["assessment_id"].startswith("risk_")
    assert assessment["case_id"] == case_id
    assert assessment["amount_at_risk"] == "4999.00"

    assert 0.0 <= assessment["risk_score"] <= 100.0
    assert 0.0 <= assessment["recoverability_score"] <= 100.0

    assert assessment["reason"]
    assert assessment["assessed_at"]


def test_risk_assessment_for_missing_case_returns_404():
    response = client.post(
        "/recovery-cases/case_does_not_exist/risk-assessments"
    )

    assert response.status_code == 404
    assert "Recovery case not found" in response.json()["detail"]

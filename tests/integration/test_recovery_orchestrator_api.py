from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def fresh_case(payment_id):
    # Each test starts its own case so the result does not depend on
    # what an earlier test or batch run left behind.
    response = client.post(f"/recovery-cases/{payment_id}")

    assert response.status_code == 200

    return response.json()["case_id"]


def test_high_risk_case_is_refused_before_any_execution():
    case_id = fresh_case("pay_2011")

    result = client.post(f"/recovery-cases/{case_id}/run").json()

    assert result["policy_decision"] == "escalate"
    assert result["stop_reason"] == "high_risk_case"
    assert result["escalated"] is True
    # The important part: the policy refused, so nothing ran at all.
    assert result["attempt_number"] == 0
    assert result["amount_recovered"] == 0.0


def test_retry_limit_stops_automation_and_escalates():
    case_id = fresh_case("pay_2014")

    result = client.post(f"/recovery-cases/{case_id}/run").json()

    assert result["attempt_number"] == result["max_attempts"] == 3
    assert result["stop_reason"] == "maximum_retry_limit_reached"
    assert result["escalated"] is True
    assert result["amount_recovered"] == 0.0


def test_successful_recovery_stops_further_work():
    case_id = fresh_case("pay_2004")

    first = client.post(f"/recovery-cases/{case_id}/run").json()

    assert first["stop_reason"] == "payment_recovered"
    assert first["amount_recovered"] > 0

    # Running again must not retry a case that already paid.
    second = client.post(f"/recovery-cases/{case_id}/run").json()

    assert second["stop_reason"] == "case_already_closed"
    assert second["attempt_number"] == 0
    assert second["audit_event_ids"] == []


def test_closed_case_is_not_executed_twice():
    case_id = fresh_case("pay_2011")

    client.post(f"/recovery-cases/{case_id}/run")
    before = len(client.get(f"/recovery-cases/{case_id}/audit-events").json())

    client.post(f"/recovery-cases/{case_id}/run")
    after = len(client.get(f"/recovery-cases/{case_id}/audit-events").json())

    # A duplicate run writes nothing, so the trail cannot fill with
    # events for work that never happened.
    assert after == before


def test_audit_events_are_recorded_in_lifecycle_order():
    case_id = fresh_case("pay_2004")
    client.post(f"/recovery-cases/{case_id}/run")

    events = client.get(f"/recovery-cases/{case_id}/audit-events").json()
    types = [event["event_type"] for event in events]

    assert types[0] == "risk_assessed"
    assert types[-1] == "case_stopped"

    # Assessment precedes the decision, which precedes authorisation,
    # which precedes execution.
    assert types.index("decision_generated") < types.index("action_authorized")
    assert types.index("action_authorized") < types.index("action_executed")
    assert types.index("action_executed") < types.index("recovery_completed")

    assert all(event["occurred_at"] for event in events)


def test_batch_metrics_match_the_database():
    body = client.post("/recovery-batch/run?limit=1").json()

    cases = client.get("/recovery-cases").json()

    at_risk = sum(float(case["amount_at_risk"]) for case in cases)
    recovered = sum(float(case["amount_recovered"]) for case in cases)

    assert body["total_revenue_at_risk"] == round(at_risk, 2)
    assert body["revenue_recovered"] == round(recovered, 2)

    # The three figures must reconcile, or the dashboard is reporting a
    # number the database does not hold.
    assert (
        round(body["revenue_recovered"] + body["remaining_revenue_at_risk"], 2)
        == body["total_revenue_at_risk"]
    )


def test_unknown_case_returns_not_found():
    assert client.post("/recovery-cases/nope/run").status_code == 404


def test_policy_endpoint_reports_the_enforced_limits():
    from app.policies.recovery_decision_policy import MAX_RETRIES

    body = client.get("/recovery-policy").json()

    assert body["max_retries"] == MAX_RETRIES
    assert body["mode"] == "test_simulation"

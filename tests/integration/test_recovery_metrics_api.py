from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def metrics():
    response = client.get("/recovery-metrics")

    assert response.status_code == 200

    return response.json()


def test_metrics_endpoint_runs_nothing():
    # Reading the figures must not process cases, or opening the
    # dashboard would silently start recovering money.
    before = metrics()
    after = metrics()

    assert before["recovery_attempts"] == after["recovery_attempts"]
    assert before["revenue_recovered"] == after["revenue_recovered"]


def test_the_three_money_figures_are_ordered():
    body = metrics()

    at_risk = body["total_revenue_at_risk"]
    recoverable = body["recoverable_revenue"]
    recovered = body["revenue_recovered"]

    # Everything at stake, what the policy cleared, what came back.
    # Recoverable can equal recovered before anything has failed, but it
    # can never exceed what was at risk or fall below what was collected.
    assert at_risk >= recoverable >= recovered


def test_revenue_figures_reconcile():
    body = metrics()

    assert (
        round(body["revenue_recovered"] + body["remaining_revenue_at_risk"], 2)
        == body["total_revenue_at_risk"]
    )


def test_case_counts_reconcile_with_the_total():
    body = metrics()

    counted = (
        body["recovered_cases"]
        + body["failed_cases"]
        + body["escalated_cases"]
        + body["stopped_cases"]
        + body["active_cases"]
    )

    assert counted == body["total_cases_evaluated"]


def test_recovered_revenue_matches_the_stored_cases():
    body = metrics()

    cases = client.get("/recovery-cases").json()
    stored = sum(float(case["amount_recovered"]) for case in cases)

    # The figure has to come from the outcomes, not from a counter the
    # endpoint keeps while looping.
    assert body["revenue_recovered"] == round(stored, 2)


def test_successful_recoveries_never_exceed_attempts():
    body = metrics()

    assert body["successful_recoveries"] <= body["recovery_attempts"]
    assert body["actions_executed"] <= body["recovery_attempts"]


def test_recovery_rate_is_recovered_over_at_risk():
    body = metrics()

    if body["total_revenue_at_risk"]:
        expected = round(
            body["revenue_recovered"] / body["total_revenue_at_risk"] * 100, 2
        )

        assert body["recovery_rate"] == expected


def test_case_detail_exposes_the_diagnosis():
    case_id = client.post("/recovery-cases/pay_2006").json()["case_id"]

    body = client.get(f"/recovery-cases/{case_id}").json()

    assert "diagnosis" in body
    # pay_2006 is seeded with an expired card, and that has to survive
    # all the way to the interface.
    assert body["diagnosis"]["category"] == "card_expired"
    assert body["diagnosis"]["retry_viable"] is False
    assert body["diagnosis"]["rationale"]

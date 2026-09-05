from app.simulator.payment_simulator import verify_payment


def test_result_is_labelled_as_simulated():
    result = verify_payment("pay_2004", 1, 90.0)

    assert result.mode == "test_simulation"


def test_same_inputs_always_give_the_same_result():
    # The demo has to replay identically; a simulator that rolled
    # randomly would tell a different story on every run.
    first = verify_payment("pay_2004", 1, 90.0)
    second = verify_payment("pay_2004", 1, 90.0)

    assert first.succeeded == second.succeeded
    assert first.detail == second.detail


def test_keyed_on_payment_not_case():
    # Case ids are uuids minted on every reset. Keying on them made the
    # outcomes change each time the data was reseeded.
    assert (
        verify_payment("pay_2004", 1, 90.0).succeeded
        != verify_payment("pay_2014", 1, 60.0).succeeded
    )


def test_first_attempt_succeeds_for_a_healthy_case():
    assert verify_payment("pay_2004", 1, 100.0).succeeded is True


def test_later_attempts_are_harder():
    # The threshold decays by 20 per attempt, so a case that is
    # borderline on the first try becomes progressively less likely.
    recoverability = 60.0

    thresholds = []
    for attempt in (1, 2, 3):
        result = verify_payment("pay_demo_decay", attempt, recoverability)
        thresholds.append(result.detail)

    assert "threshold 60" in thresholds[0]
    assert "threshold 40" in thresholds[1]
    assert "threshold 20" in thresholds[2]


def test_threshold_never_goes_negative():
    result = verify_payment("pay_demo_floor", 3, 10.0)

    assert "threshold 0" in result.detail
    assert result.succeeded is False


def test_seeded_case_fails_every_attempt():
    # pay_2014 is seeded specifically to exhaust the retry ladder, so the
    # escalation path has something to demonstrate.
    outcomes = [
        verify_payment("pay_2014", attempt, 60.0).succeeded
        for attempt in (1, 2, 3)
    ]

    assert outcomes == [False, False, False]

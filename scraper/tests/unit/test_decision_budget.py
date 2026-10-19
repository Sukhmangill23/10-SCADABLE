import pytest

from scraper.decision_budget import DecisionBudget, request_size


def test_reservations_use_utf8_size_and_reconcile_reported_usage():
    payload = {"input": "Evidence: café", "questions": []}
    budget = DecisionBudget(0.03)
    reservation = budget.reserve(payload)
    assert reservation.tokens == request_size(payload) + 1024
    assert budget.limit_tokens == 300_000
    assert budget.reserved_tokens == reservation.tokens
    budget.settle(reservation, reported_input_tokens=120)
    assert budget.reported_input_tokens == 120
    assert budget.reserved_tokens == 0
    assert budget.uncertain_input_tokens == 0
    assert budget.estimated_cost_usd == pytest.approx(0.000012)


def test_unknown_usage_keeps_the_reservation_charged_and_blocks_overspending():
    payload = {"input": "evidence"}
    tokens = request_size(payload) + 1024
    budget = DecisionBudget(tokens * 0.10 / 1_000_000)
    reservation = budget.reserve(payload)
    assert reservation is not None
    assert budget.reserve(payload) is None
    budget.settle(reservation, reported_input_tokens=None)
    assert budget.uncertain_input_tokens == tokens
    assert budget.reserve(payload) is None
    assert budget.reserved_tokens == 0
    with pytest.raises(ValueError, match="settled"):
        budget.settle(reservation, reported_input_tokens=1)


def test_competitor_budgets_are_independent_and_reported_overruns_block_new_calls():
    payload = {"input": "one"}
    first, second = DecisionBudget(0.03), DecisionBudget(0.03)
    reservation = first.reserve(payload)
    first.settle(reservation, reported_input_tokens=300_001)
    assert first.reserve(payload) is None
    assert second.reserve(payload) is not None


def test_zero_budget_never_reserves_and_invalid_accounting_is_rejected():
    assert DecisionBudget(0.0).reserve({"input": "x"}) is None
    with pytest.raises(ValueError):
        DecisionBudget(-0.01)
    budget = DecisionBudget(0.03)
    reservation = budget.reserve({"input": "x"})
    with pytest.raises(ValueError):
        budget.settle(reservation, reported_input_tokens=-1)
    assert budget.reserved_tokens == reservation.tokens


def test_one_budget_cannot_settle_another_budgets_reservation():
    first, second = DecisionBudget(0.03), DecisionBudget(0.03)
    reservation = first.reserve({"input": "x"})
    with pytest.raises(ValueError):
        second.settle(reservation, reported_input_tokens=10)
    assert first.reserved_tokens == reservation.tokens

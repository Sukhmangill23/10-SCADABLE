"""Tests for citation validation, SWOT change detection, and cache keys."""

import pytest

from app.core.baseline import get_scadable_baseline
from app.llm.usage import UsageTracker
from app.llm.validation import compute_swot_changes, normalize_url
from app.llm.versioning import build_cache_key, build_versions, is_cache_valid

SCRAPED = {"competitor_name": "Vanta", "pages": [{"url": "https://vanta.com/a", "text": "hi"}]}


def test_normalize_url():
    assert normalize_url("HTTPS://WWW.Vanta.com/Pricing/#x") == "https://vanta.com/Pricing"


def test_swot_changes_added_removed_unchanged():
    prev = [
        {"category": "strength", "content": "Broad integrations."},
        {"category": "threat", "content": "Big budget"},
    ]
    curr = [
        {"category": "strength", "content": "broad   integrations"},
        {"category": "weakness", "content": "No CRA."},
    ]
    changes = compute_swot_changes(prev, curr)
    assert changes["counts"] == {"added": 1, "removed": 1, "unchanged": 1}
    assert changes["added"][0]["category"] == "weakness"
    assert changes["removed"][0]["category"] == "threat"


def test_swot_changes_without_previous():
    changes = compute_swot_changes(None, [{"category": "strength", "content": "x"}])
    assert changes["has_previous"] is False and changes["counts"]["added"] == 1


def test_cache_key_is_deterministic_and_sensitive():
    k1 = build_cache_key("h", "p1", "b1", "m")
    assert k1 == build_cache_key("h", "p1", "b1", "m")
    assert k1 != build_cache_key("h", "p2", "b1", "m")
    assert k1 != build_cache_key("h", "p1", "b1", "other-model")


def test_is_cache_valid():
    baseline = get_scadable_baseline()
    cached = {"analysis_mode": "real", "versions": build_versions(SCRAPED, baseline, "m")}
    assert is_cache_valid(cached, SCRAPED, baseline, "m")
    assert not is_cache_valid(cached, SCRAPED, baseline, "other-model")
    changed = {**SCRAPED, "pages": [{"url": "https://vanta.com/a", "text": "new"}]}
    assert not is_cache_valid(cached, changed, baseline, "m")
    assert not is_cache_valid({**cached, "analysis_mode": "mock"}, SCRAPED, baseline, "m")
    assert not is_cache_valid(None, SCRAPED, baseline, "m")


def test_usage_cost_null_without_pricing():
    tracker = UsageTracker(model="m")
    tracker.record("extract", 100, 50)
    data = tracker.to_dict()
    assert data["estimated_cost_usd"] is None and data["pricing_configured"] is False
    assert data["total_tokens"] == 150


def test_luna_request_cost_and_long_context():
    from app.llm.pricing import get_pricing, request_cost_usd

    luna = get_pricing("gpt-5.6-luna")
    assert request_cost_usd(luna, 100_000, 100_000) == pytest.approx((100_000 * 0.20 + 100_000 * 1.20) / 1e6)
    # Cached + cache-write input at their own rates.
    assert request_cost_usd(luna, 200_000, 0, 100_000, 100_000) == pytest.approx(
        (100_000 * 0.02 + 100_000 * 0.25) / 1e6
    )
    # Over 272K input tokens: whole request at 2x input and 1.5x output.
    assert request_cost_usd(luna, 300_000, 100_000) == pytest.approx(
        (300_000 * 0.40 + 100_000 * 1.80) / 1e6
    )
    assert request_cost_usd(None, 10, 10) is None


def test_check_project_budget_thresholds(caplog):
    import logging

    from app.llm.pricing import check_project_budget

    with caplog.at_level(logging.WARNING):
        low = check_project_budget(10.0, 100.0)
    assert low["thresholds_crossed"] == [] and caplog.text == ""

    with caplog.at_level(logging.WARNING):
        high = check_project_budget(85.0, 100.0, next_run_estimate_usd=0.01)
    assert high["thresholds_crossed"] == [0.5, 0.8] and high["allowed"] is True
    assert "past the 80% threshold" in caplog.text
    assert check_project_budget(99.995, 100.0, 0.01)["allowed"] is False

"""Tests for citation validation, SWOT change detection, and cache keys."""

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

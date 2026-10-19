import pytest
from pydantic import ValidationError

from scraper import ScraperConfig
from scraper.discovery.relevance import UrlPolicy


def test_url_policy_never_assigns_keyword_scores():
    policy = UrlPolicy("https://pricing.example/", ScraperConfig())
    assert not hasattr(policy, "score")
    assert policy.evaluate("https://pricing.example/opaque").disposition == "pending"


def test_external_links_are_recorded_without_keyword_evidence():
    policy = UrlPolicy("https://example.com/", ScraperConfig())
    assert policy.evaluate("https://external.example/opaque").disposition == "external"


@pytest.mark.parametrize("path", ["/login", "/privacy", "/report.pdf", "/assets/app.js"])
def test_irrelevant_and_non_html_pages_are_not_eligible(path):
    policy = UrlPolicy("https://example.com/", ScraperConfig())
    decision = policy.evaluate("https://example.com" + path)
    assert decision.disposition == "skipped"
    assert decision.reason in {"excluded_pattern", "unsupported_extension"}


def test_global_hub_pages_remain_eligible_with_default_threshold():
    policy = UrlPolicy("https://example.com/", ScraperConfig())
    assert policy.evaluate("https://example.com/opaque").disposition == "pending"


@pytest.mark.parametrize(
    "field,value",
    [
        ("category_keywords", {"pricing": ["plans"]}),
        ("minimum_relevance_score", 0.0),
        ("url_keyword_weight", 0.7),
        ("title_keyword_weight", 0.3),
    ],
)
def test_removed_keyword_settings_give_actionable_migration_errors(field, value):
    with pytest.raises(ValidationError) as error:
        ScraperConfig.model_validate({field: value})
    assert field in str(error.value)
    assert "selection.objective" in str(error.value)
    assert "selection.mode='structural'" in str(error.value)

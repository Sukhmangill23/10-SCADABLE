import pytest
from pydantic import ValidationError

from scraper import ScraperConfig
from scraper.discovery.relevance import UrlPolicy


def test_keyword_scoring_ignores_hostnames_and_uses_known_titles():
    policy = UrlPolicy("https://pricing.example/", ScraperConfig())
    assert policy.score("https://pricing.example/opaque") == 0
    assert policy.score("https://pricing.example/opaque", "Pricing plans") > 0
    assert policy.score("https://pricing.example/pricing") > 0


def test_a_disabled_url_signal_does_not_contribute_to_relevance():
    policy = UrlPolicy(
        "https://example.com/",
        ScraperConfig(
            url_keyword_weight=0.0,
            title_keyword_weight=1.0,
        ),
    )
    assert policy.score("https://example.com/pricing") == 0
    assert policy.score("https://example.com/opaque", "Careers") > 0


@pytest.mark.parametrize("path", ["/login", "/privacy", "/report.pdf", "/assets/app.js"])
def test_irrelevant_and_non_html_pages_are_not_eligible(path):
    policy = UrlPolicy("https://example.com/", ScraperConfig())
    decision = policy.evaluate("https://example.com" + path)
    assert decision.disposition == "skipped"
    assert decision.reason in {"excluded_pattern", "unsupported_extension"}


def test_global_hub_pages_remain_eligible_with_default_threshold():
    policy = UrlPolicy("https://example.com/", ScraperConfig())
    assert policy.evaluate("https://example.com/opaque").disposition == "pending"


def test_relevance_threshold_does_not_prevent_fetching_the_starting_homepage():
    policy = UrlPolicy("https://example.com/", ScraperConfig(minimum_relevance_score=0.5))
    assert policy.evaluate("https://example.com/", homepage=True).disposition == "pending"
    assert policy.evaluate("https://example.com/opaque").reason == "below_relevance_threshold"


def test_relevance_requires_at_least_one_enabled_signal():
    with pytest.raises(ValidationError):
        ScraperConfig(url_keyword_weight=0.0, title_keyword_weight=0.0)

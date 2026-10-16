import json
from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from scadable_scraper.models import (
    CompetitorCrawlResult,
    CompetitorInput,
    DiscoveredUrl,
    ScrapedPage,
)


def page_data(**changes):
    return {
        "competitor_name": "Example",
        "homepage_url": "https://example.com/",
        "source_url": "https://example.com/pricing?currency=cad",
        "final_url": "https://www.example.com/pricing?currency=cad",
        "page_title": "Pricing",
        "page_category": "pricing",
        "crawl_timestamp": datetime(2026, 10, 16, 10, tzinfo=timezone(timedelta(hours=-4))),
        "crawl_status": "success",
        "http_status": 200,
        "raw_markdown": "# Plans\n\n| Plan | Price |\n| Pro | $49 |",
        "filtered_markdown": "# Plans\n\n| Plan | Price |\n| Pro | $49 |",
        "cleaned_markdown": "# Plans\n\n| Plan | Price |\n| Pro | $49 |",
        "metadata": {"description": "Plans", "json_ld": [{"price": 49}]},
        **changes,
    }


def test_page_json_preserves_provenance_and_normalizes_timestamp_to_utc():
    page = ScrapedPage(**page_data())
    payload = json.loads(page.model_dump_json())
    assert payload["source_url"] == "https://example.com/pricing?currency=cad"
    assert payload["final_url"] == "https://www.example.com/pricing?currency=cad"
    assert payload["crawl_timestamp"] == "2026-10-16T14:00:00Z"
    assert payload["metadata"]["json_ld"][0]["price"] == 49
    assert "| Pro | $49 |" in payload["raw_markdown"]
    assert ScrapedPage.model_validate_json(page.model_dump_json()) == page


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com",
        "example.com",
        "https://a:b@example.com",
        "https://example.com/a",
        "https://example.com/?query=1",
        "https://example.com/#section",
    ],
)
def test_input_requires_an_http_homepage_without_credentials(url):
    with pytest.raises(ValidationError):
        CompetitorInput(homepage_url=url)


def test_optional_name_uses_hostname_and_accepts_multiple_competitor_inputs():
    assert CompetitorInput(homepage_url="https://www.example.com").display_name == "example.com"
    assert CompetitorInput(homepage_url="http://example.org", name="Example Org").display_name == (
        "Example Org"
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"crawl_timestamp": datetime(2026, 10, 16)},
        {"crawl_status": "failed", "error_message": None},
        {"crawl_status": "failed", "error_message": "  "},
        {"crawl_status": "success", "error_message": "contradiction"},
        {"crawl_status": "success", "http_status": 404},
        {"raw_markdown": " "},
        {"attempt_count": 0},
        {"unexpected": True},
    ],
)
def test_invalid_page_outcomes_are_rejected(changes):
    with pytest.raises(ValidationError):
        ScrapedPage(**page_data(**changes))


def test_failed_page_can_preserve_partial_content():
    page = ScrapedPage(**page_data(crawl_status="failed", error_message="Timed out"))
    assert page.raw_markdown.startswith("# Plans")
    assert page.error_message == "Timed out"


def test_result_derives_counts_and_round_trips_without_losing_url_dispositions():
    result = CompetitorCrawlResult(
        competitor_name="Example",
        homepage_url="https://example.com/",
        started_at=datetime(2026, 10, 16, 14, tzinfo=UTC),
        finished_at=datetime(2026, 10, 16, 14, 1, tzinfo=UTC),
        run_status="partial",
        completion_reason="page_limit",
        pages=[ScrapedPage(**page_data())],
        discovered_urls=[
            DiscoveredUrl(
                url="https://example.com/pricing?currency=cad",
                normalized_url="https://example.com/pricing?currency=cad",
                discovery_source="internal_link",
                disposition="crawled",
                depth=1,
            ),
            DiscoveredUrl(
                url="https://example.com/blog",
                normalized_url="https://example.com/blog",
                discovery_source="sitemap",
                disposition="deferred",
                reason="page_limit",
                depth=1,
                depth_basis="sitemap_seed",
            ),
            DiscoveredUrl(
                url="https://jobs.example.net/acme",
                normalized_url="https://jobs.example.net/acme",
                discovery_source="external_link",
                disposition="external",
                reason="domain_not_approved",
            ),
            DiscoveredUrl(
                url="https://example.com/login",
                normalized_url="https://example.com/login",
                discovery_source="internal_link",
                disposition="skipped",
                reason="excluded_pattern",
                depth=1,
            ),
        ],
    )
    payload = json.loads(result.model_dump_json())
    assert payload["schema_version"] == "1.0"
    assert payload["summary"] == {
        "successful": 1,
        "failed": 0,
        "skipped": 1,
        "discovered": 4,
        "deferred": 1,
        "external": 1,
        "pending": 0,
    }
    restored = CompetitorCrawlResult.model_validate_json(result.model_dump_json())
    assert restored.summary == result.summary
    assert restored.discovered_urls[1].reason == "page_limit"


def test_result_rejects_backwards_time_and_mismatched_competitor_pages():
    base = {
        "competitor_name": "Example",
        "homepage_url": "https://example.com/",
        "started_at": datetime(2026, 10, 16, 14, tzinfo=UTC),
        "finished_at": datetime(2026, 10, 16, 13, tzinfo=UTC),
        "run_status": "failed",
        "completion_reason": "failed",
    }
    with pytest.raises(ValidationError):
        CompetitorCrawlResult(**base)
    with pytest.raises(ValidationError):
        CompetitorCrawlResult(
            **{
                **base,
                "finished_at": base["started_at"],
                "pages": [
                    ScrapedPage(**page_data(homepage_url="https://other.example/")),
                ],
            }
        )

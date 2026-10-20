from datetime import UTC, datetime

import pytest

from scraper import ScraperConfig


@pytest.mark.parametrize(
    "status,kind,want",
    [
        (408, None, True),
        (429, None, True),
        (500, None, True),
        (502, None, True),
        (503, None, True),
        (504, None, True),
        (404, None, False),
        (403, None, False),
        (501, None, False),
        (None, "timeout", True),
        (None, "network", True),
        (None, "capacity", False),
        (None, "policy", False),
        (None, "empty_content", False),
        (None, "internal", False),
        (200, None, False),
    ],
)
def test_only_transient_failures_are_retryable(status, kind, want):
    from scraper.reliability import is_retryable

    assert is_retryable(status, kind) is want


@pytest.mark.parametrize(
    "header,want",
    [
        ("5", 5.0),
        ("-1", None),
        ("bad", None),
        ("inf", None),
        ("Thu, 01 Jan 2026 00:00:10 GMT", 10.0),
        ("Wed, 31 Dec 2025 23:59:59 GMT", 0.0),
    ],
)
def test_retry_after_supports_seconds_and_http_dates(header, want):
    from scraper.reliability import parse_retry_after

    assert parse_retry_after(header, now=datetime(2026, 1, 1, tzinfo=UTC)) == want


def test_delay_is_exponential_bounded_and_never_shortens_retry_after(monkeypatch):
    from scraper.reliability import retry_delay

    monkeypatch.setattr("scraper.reliability.random.uniform", lambda low, high: high)
    settings = ScraperConfig(max_backoff_seconds=3.0)
    assert [retry_delay(n, settings) for n in [1, 2, 3, 9]] == [1.0, 2.0, 3.0, 3.0]
    assert retry_delay(1, settings, retry_after=2.5) == 2.5
    assert retry_delay(1, settings, retry_after=4.0) is None

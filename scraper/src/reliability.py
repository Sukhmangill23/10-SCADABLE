"""Small shared retry policy; callers own attempts, resource budgets and sleeping."""

import asyncio
import random
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from .config import ScraperConfig
from .models import FetchedPage
from .types import utc_now

TRANSIENT_STATUSES = frozenset({408, 429, 500, 502, 503, 504})


class CapacityTimeout(TimeoutError):
    """Capacity/rate waits are bounded separately and are not network retry signals."""


class FetchAttemptError(Exception):
    def __init__(self, message: str, kind: str):
        self.kind = kind
        super().__init__(message)


def exception_kind(error: Exception) -> str:
    if isinstance(error, FetchAttemptError):
        return error.kind
    if isinstance(error, CapacityTimeout):
        return "capacity"
    if isinstance(error, TimeoutError):
        return "timeout"
    if isinstance(error, ConnectionError):
        return "network"
    return "internal"


def failed_page(url: str, error: Exception, *, kind: str | None = None) -> FetchedPage:
    return FetchedPage(
        source_url=url,
        crawl_timestamp=utc_now(),
        crawl_status="failed",
        error_message=f"{type(error).__name__}: {error}",
        metadata={"crawl_diagnostics": {"failure_kind": kind or exception_kind(error)}},
    )


async def wait_before_retry(delay: float) -> None:
    await asyncio.sleep(delay)


def is_retryable(status: int | None, failure_kind: str | None) -> bool:
    # Explicit policy/internal failures always take precedence over incidental HTTP data.
    if failure_kind in {"capacity", "policy", "internal", "extraction", "empty_content"}:
        return False
    return status in TRANSIENT_STATUSES or failure_kind in {"network", "timeout"}


def parse_retry_after(value: str | None, *, now: datetime | None = None) -> float | None:
    if not value:
        return None
    value = value.strip()
    if value.isascii() and value.isdigit():
        # Avoid huge integer/float inputs from untrusted response headers.
        return float(value) if len(value) < 16 else float("inf")
    try:
        target = parsedate_to_datetime(value)
        if target.tzinfo is None:
            return None
        return max(0.0, (target - (now or datetime.now(UTC))).total_seconds())
    except (TypeError, ValueError, OverflowError):
        return None


def retry_delay(
    attempt: int, settings: ScraperConfig, *, retry_after: float | None = None
) -> float | None:
    if retry_after is not None and retry_after > settings.max_backoff_seconds:
        return None
    ceiling = min(settings.max_backoff_seconds, 2.0 ** min(attempt - 1, 30))
    return max(random.uniform(ceiling / 2, ceiling), retry_after or 0.0)

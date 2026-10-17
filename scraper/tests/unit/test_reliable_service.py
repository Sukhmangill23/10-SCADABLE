import asyncio

import httpx
import pytest

from scraper import CompetitorInput, FetchedPage, ScraperConfig
from scraper.models import DiscoveredLink
from scraper.types import utc_now


def response(url, status=200, **kwargs):
    return FetchedPage(
        source_url=url,
        crawl_timestamp=utc_now(),
        http_status=status,
        crawl_status="success" if status < 400 else "failed",
        error_message=None if status < 400 else f"http_{status}",
        raw_markdown="Plans: $49",
        **kwargs,
    )


def settings(**kwargs):
    return ScraperConfig(
        max_pages=1, max_backoff_seconds=0.001, request_delay_seconds=(0.0, 0.0), **kwargs
    )


def service(fetcher, **kwargs):
    from scraper.service import CompetitorScraper

    transport = httpx.MockTransport(lambda r: httpx.Response(404))
    return CompetitorScraper(
        fetcher_factory=lambda *args: fetcher, http_transport=transport, **kwargs
    )


class Fetcher:
    def __init__(self, operation):
        self.operation = operation
        self.calls = []
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        self.closed = True

    async def fetch(self, url, config):
        self.calls.append(str(url))
        return await self.operation(str(url), len(self.calls))


async def test_transient_page_retries_share_one_frontier_slot_and_record_history():
    async def operation(url, count):
        if count < 3:
            raise TimeoutError("transient navigation timeout")
        return response(url)

    fetcher = Fetcher(operation)
    result = await service(fetcher).crawl(
        CompetitorInput(homepage_url="https://example.com"), settings()
    )
    assert result.summary.successful == 1
    assert len(result.discovered_urls) == 1
    assert fetcher.calls == ["https://example.com/"] * 3
    page = result.pages[0]
    assert page.attempt_count == 3
    history = page.metadata["crawl_diagnostics"]["attempts"]
    assert (
        page.metadata["crawl_diagnostics"]["duration_seconds"]
        >= sum(item["duration_seconds"] for item in history) - 0.00001
    )
    assert [attempt["failure_kind"] for attempt in history] == ["timeout", "timeout", None]
    assert fetcher.closed


@pytest.mark.parametrize("status,expected", [(503, 3), (429, 3), (403, 1), (404, 1), (501, 1)])
async def test_http_retry_policy_and_exhaustion(status, expected):
    async def operation(url, count):
        return response(url, status)

    fetcher = Fetcher(operation)
    result = await service(fetcher).crawl(
        CompetitorInput(homepage_url="https://example.com"), settings()
    )
    assert len(fetcher.calls) == expected
    assert result.summary.failed == 1
    assert result.pages[0].attempt_count == expected
    assert result.pages[0].raw_markdown == "Plans: $49"


async def test_long_retry_after_stops_without_retrying_early():
    async def operation(url, count):
        return response(url, 429, metadata={"response_headers": {"Retry-After": "120"}})

    fetcher = Fetcher(operation)
    result = await service(fetcher).crawl(
        CompetitorInput(homepage_url="https://example.com"), settings()
    )
    assert len(fetcher.calls) == 1
    assert (
        result.pages[0].metadata["crawl_diagnostics"]["stop_reason"] == "retry_after_exceeds_budget"
    )


async def test_global_queue_wait_does_not_consume_render_timeout():
    from scraper.service import CompetitorScraper

    async def operation(url, count):
        await asyncio.sleep(0.06 if "slow" in url else 0.001)
        return response(url)

    fetchers = []

    def factory(*args):
        fetcher = Fetcher(operation)
        fetchers.append(fetcher)
        return fetcher

    scraper = CompetitorScraper(
        fetcher_factory=factory, http_transport=httpx.MockTransport(lambda r: httpx.Response(404))
    )
    inputs = [
        CompetitorInput(
            homepage_url="https://slow.example", overrides={"page_timeout_seconds": 0.2}
        ),
        CompetitorInput(
            homepage_url="https://fast.example", overrides={"page_timeout_seconds": 0.02}
        ),
    ]
    results = [result async for result in scraper.crawl_many(inputs, settings(max_concurrency=1))]
    assert all(result.summary.successful == 1 for result in results)
    assert sum(len(fetcher.calls) for fetcher in fetchers) == 2


async def test_one_extraction_error_preserves_other_pages_and_source():
    from scraper.extraction import MarkdownExtractor

    class Extractor:
        def extract(self, page, competitor, config):
            if str(page.source_url).endswith("/pricing"):
                raise ValueError("fixture malformed extraction")
            return MarkdownExtractor().extract(page, competitor, config)

    async def operation(url, count):
        links = (
            [
                DiscoveredLink(url="https://example.com/pricing"),
                DiscoveredLink(url="https://example.com/products"),
            ]
            if url.endswith("/")
            else []
        )
        return response(url, links=links)

    scraper = service(Fetcher(operation), extractor=Extractor())
    result = await scraper.crawl(
        CompetitorInput(homepage_url="https://example.com"),
        ScraperConfig(max_pages=3, request_delay_seconds=(0.0, 0.0)),
    )
    assert result.summary.successful == 2
    assert result.summary.failed == 1
    assert result.run_status == "partial"
    failed = next(page for page in result.pages if page.crawl_status == "failed")
    assert failed.raw_markdown == "Plans: $49"
    assert failed.metadata["crawl_diagnostics"]["failure_kind"] == "extraction"


async def test_backoff_releases_global_capacity(monkeypatch):
    from scraper.service import CompetitorScraper

    retry_waiting = asyncio.Event()
    other_done = asyncio.Event()

    async def backoff(delay):
        retry_waiting.set()
        await asyncio.wait_for(other_done.wait(), 1)

    monkeypatch.setattr("scraper.service.wait_before_retry", backoff)

    async def operation(url, count):
        if "retry" in url and count == 1:
            return response(url, 503)
        if "other" in url:
            await retry_waiting.wait()
            other_done.set()
        return response(url)

    scraper = CompetitorScraper(
        fetcher_factory=lambda *args: Fetcher(operation),
        http_transport=httpx.MockTransport(lambda r: httpx.Response(404)),
    )
    inputs = [
        CompetitorInput(homepage_url=f"https://{name}.example") for name in ["retry", "other"]
    ]
    results = [r async for r in scraper.crawl_many(inputs, settings(max_concurrency=1))]
    assert all(r.summary.successful == 1 for r in results)


async def test_capacity_wait_timeout_is_not_retried():
    from scraper.service import CompetitorScraper

    calls = []

    async def operation(url, count):
        calls.append(url)
        await asyncio.sleep(0.06)
        return response(url)

    scraper = CompetitorScraper(
        fetcher_factory=lambda *args: Fetcher(operation),
        http_transport=httpx.MockTransport(lambda r: httpx.Response(404)),
    )
    inputs = [
        CompetitorInput(homepage_url="https://slow.example"),
        CompetitorInput(
            homepage_url="https://queued.example", overrides={"capacity_wait_timeout_seconds": 0.01}
        ),
    ]
    results = [r async for r in scraper.crawl_many(inputs, settings(max_concurrency=1))]
    queued = next(r for r in results if r.homepage_url.host == "queued.example")
    assert queued.pages[0].attempt_count == 1
    assert queued.pages[0].metadata["crawl_diagnostics"]["failure_kind"] == "capacity"
    assert calls == ["https://slow.example/"]


async def test_cancellation_during_backoff_propagates_and_closes_fetcher(monkeypatch):
    waiting = asyncio.Event()

    async def backoff(delay):
        waiting.set()
        await asyncio.Event().wait()

    monkeypatch.setattr("scraper.service.wait_before_retry", backoff)

    async def operation(url, count):
        return response(url, 503)

    fetcher = Fetcher(operation)
    task = asyncio.create_task(
        service(fetcher).crawl(CompetitorInput(homepage_url="https://example.com"), settings())
    )
    await waiting.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert fetcher.closed
    assert len(fetcher.calls) == 1


async def test_long_retry_after_prevents_requests_to_other_pages_on_same_host():
    async def operation(url, count):
        if url.endswith("/pricing"):
            return response(url, 429, metadata={"response_headers": {"retry-after": "120"}})
        links = (
            [
                DiscoveredLink(url="https://example.com/pricing"),
                DiscoveredLink(url="https://example.com/products"),
            ]
            if url.endswith("/")
            else []
        )
        return response(url, links=links)

    fetcher = Fetcher(operation)
    result = await service(fetcher).crawl(
        CompetitorInput(homepage_url="https://example.com"),
        ScraperConfig(max_pages=3, request_delay_seconds=(0.0, 0.0)),
    )
    assert fetcher.calls == ["https://example.com/", "https://example.com/pricing"]
    assert result.summary.successful == 1


async def test_page_retry_after_also_prevents_sitemap_requests_on_same_host():
    from scraper.service import CompetitorScraper

    requested = []

    def handler(request):
        requested.append(request.url.path)
        return httpx.Response(404)

    async def operation(url, count):
        return response(url, 429, metadata={"response_headers": {"retry-after": "120"}})

    scraper = CompetitorScraper(
        fetcher_factory=lambda *args: Fetcher(operation),
        http_transport=httpx.MockTransport(handler),
    )
    result = await scraper.crawl(CompetitorInput(homepage_url="https://example.com"), settings())
    assert result.summary.failed == 1
    assert requested == ["/robots.txt"]

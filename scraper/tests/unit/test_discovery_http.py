import httpx
import pytest

from scadable_scraper import ScraperConfig
from scadable_scraper.discovery.http import GuardedHttpClient, RequestBlocked


async def test_longest_robots_rule_and_wildcards_are_respected():
    body = b"User-agent: *\nAllow: /\nDisallow: /private\nDisallow: /*.pdf$\n"
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=body))
    async with GuardedHttpClient(
        "https://example.com/",
        ScraperConfig(
            request_delay_seconds=(0.0, 0.0),
        ),
        transport=transport,
    ) as client:
        for url in ("https://example.com/private", "https://example.com/report.pdf"):
            with pytest.raises(RequestBlocked, match="robots_disallowed"):
                await client.check(url)
        assert await client.check("https://example.com/pricing") == 0.0


async def test_robots_interval_is_returned_and_applied_to_sitemap_requests(monkeypatch):
    delays = []

    async def capture_delay(seconds):
        delays.append(seconds)

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200, content=b"User-agent: *\nCrawl-delay: 2\nRequest-rate: 1/5\n"
            )
        return httpx.Response(200, content=b"<urlset/>")

    monkeypatch.setattr("scadable_scraper.discovery.http.asyncio.sleep", capture_delay)
    monkeypatch.setattr("scadable_scraper.discovery.http.time.monotonic", lambda: 100.0)
    async with GuardedHttpClient(
        "https://example.com/",
        ScraperConfig(
            request_delay_seconds=(0.0, 0.0),
        ),
        transport=httpx.MockTransport(handler),
    ) as client:
        assert await client.check("https://example.com/pricing") == 5.0
        await client.document("https://example.com/sitemap.xml")
    assert delays == [5.0]


async def test_robots_failure_is_cached_and_never_treated_as_permission():
    requested = []

    def handler(request):
        requested.append(str(request.url))
        return httpx.Response(503)

    async with GuardedHttpClient(
        "https://example.com/",
        ScraperConfig(
            request_delay_seconds=(0.0, 0.0),
        ),
        transport=httpx.MockTransport(handler),
    ) as client:
        for path in ("/pricing", "/products"):
            with pytest.raises(RequestBlocked, match="robots_unavailable"):
                await client.check("https://example.com" + path)
    assert requested == ["https://example.com/robots.txt"]

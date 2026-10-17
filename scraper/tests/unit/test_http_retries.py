import httpx
import pytest

from scadable_scraper import ScraperConfig
from scadable_scraper.discovery.http import GuardedHttpClient, RequestBlocked


def settings(**kwargs):
    return ScraperConfig(request_delay_seconds=(0.0, 0.0), max_backoff_seconds=0.001, **kwargs)


async def test_http_transient_retries_consume_request_budget():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(503 if len(calls) < 4 else 200, text="<urlset/>")

    async with GuardedHttpClient(
        "https://example.com", settings(), transport=httpx.MockTransport(handler)
    ) as client:
        document = await client.document("https://example.com/sitemap.xml")
        assert document.status == 200
        assert client.request_count == 4
    assert calls == ["/robots.txt", "/sitemap.xml", "/sitemap.xml", "/sitemap.xml"]


async def test_retry_cannot_exceed_http_request_limit():
    async with GuardedHttpClient(
        "https://example.com",
        settings(max_sitemap_requests=2),
        transport=httpx.MockTransport(lambda r: httpx.Response(503)),
    ) as client:
        with pytest.raises(RequestBlocked, match="sitemap_request_limit"):
            await client.document("https://example.com/sitemap.xml")
        assert client.request_count == 2


async def test_network_error_can_recover_during_robots_fetch():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if len(calls) == 1:
            raise httpx.ConnectError("temporary reset")
        return httpx.Response(404)

    async with GuardedHttpClient(
        "https://example.com", settings(), transport=httpx.MockTransport(handler)
    ) as client:
        assert await client.check("https://example.com/pricing") == 0
    assert len(calls) == 2


async def test_long_retry_after_blocks_more_requests_to_same_host():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return (
            httpx.Response(404)
            if request.url.path == "/robots.txt"
            else httpx.Response(429, headers={"Retry-After": "120"})
        )

    async with GuardedHttpClient(
        "https://example.com", settings(), transport=httpx.MockTransport(handler)
    ) as client:
        assert (await client.document("https://example.com/sitemap.xml")).status == 429
        with pytest.raises(RequestBlocked, match="retry_after_exceeds_budget"):
            await client.document("https://example.com/sitemap_index.xml")
    assert calls == ["/robots.txt", "/sitemap.xml"]


async def test_policy_denial_and_permanent_errors_never_retry():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return (
            httpx.Response(200, text="User-agent: *\nDisallow: /private\n")
            if request.url.path == "/robots.txt"
            else httpx.Response(403)
        )

    async with GuardedHttpClient(
        "https://example.com", settings(), transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(RequestBlocked, match="robots_disallowed"):
            await client.document("https://example.com/private")
        assert (await client.document("https://example.com/sitemap.xml")).status == 403
    assert calls == ["/robots.txt", "/sitemap.xml"]

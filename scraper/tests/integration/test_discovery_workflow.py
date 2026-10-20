"""The real discovery components together, with only HTTP and rendering replaced."""

from datetime import UTC, datetime

import httpx

from scraper import CompetitorInput, FetchedPage, ScraperConfig
from scraper.discovery.engine import DiscoveryCrawler, DiscoveryRun
from scraper.discovery.http import GuardedHttpClient
from scraper.discovery.sitemaps import BoundedSitemapDiscoverer
from scraper.models import DiscoveredLink


async def test_robots_sitemaps_and_rendered_links_share_scope_and_limits():
    requested_documents = []
    rendered_urls = []

    def documents(request):
        requested_documents.append(str(request.url))
        assert request.headers["user-agent"] == "ScraperBot/0.1"
        if request.url.path == "/robots.txt":
            return httpx.Response(200, content=b"User-agent: *\nDisallow: /private\n")
        if request.url.path == "/sitemap.xml":
            return httpx.Response(
                200,
                content=(
                    b"<urlset><url><loc>https://example.com/pricing</loc></url>"
                    b"<url><loc>https://example.com/private</loc></url></urlset>"
                ),
            )
        return httpx.Response(404)

    class RenderedFixturePages:
        closed = False

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            self.closed = True

        async def fetch(self, url, settings):
            rendered_urls.append(str(url))
            links = (
                [
                    "https://example.com/pricing?utm_source=nav",
                    "https://jobs.vendor.example/careers",
                ]
                if str(url) == "https://example.com/"
                else ["https://example.com/features"]
            )
            return FetchedPage(
                source_url=url,
                final_url=url,
                crawl_timestamp=datetime.now(UTC),
                crawl_status="success",
                http_status=200,
                raw_html="<main>Fixture</main>",
                raw_markdown="# Fixture",
                links=[DiscoveredLink(url=link) for link in links],
            )

    config = ScraperConfig(
        selection={"mode": "structural"}, max_pages=4, request_delay_seconds=(0.0, 0.0)
    )
    fetcher = RenderedFixturePages()
    reader = BoundedSitemapDiscoverer(transport=httpx.MockTransport(documents))
    async with GuardedHttpClient(
        "https://example.com/", config, transport=httpx.MockTransport(documents)
    ) as guard:
        result = await DiscoveryCrawler(fetcher, reader, robots_guard=guard).run(
            CompetitorInput(homepage_url="https://example.com/"),
            config,
        )

    assert rendered_urls == [
        "https://example.com/",
        "https://example.com/pricing",
        "https://example.com/features",
    ]
    assert result.attempted_pages == 3
    records = {str(item.normalized_url): item for item in result.discovered_urls}
    assert records["https://example.com/private"].reason == "robots_disallowed"
    assert records["https://jobs.vendor.example/careers"].disposition == "external"
    assert records["https://example.com/pricing"].discovery_count >= 2
    assert all("jobs.vendor.example" not in url for url in requested_documents)
    assert fetcher.closed
    restored = DiscoveryRun.model_validate_json(result.model_dump_json())
    assert restored.attempted_pages == 3
    assert len(restored.fetched_pages) == 3

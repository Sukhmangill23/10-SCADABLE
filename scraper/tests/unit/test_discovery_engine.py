import asyncio
from datetime import UTC, datetime

import pytest

from scraper import CompetitorInput, FetchedPage, ScraperConfig
from scraper.discovery.engine import DiscoveryCrawler
from scraper.discovery.http import RequestBlocked
from scraper.interfaces import DiscoveryBatch
from scraper.models import DiscoveredLink, DiscoveredUrl


class FixtureFetcher:
    def __init__(self, pages):
        self.pages = pages
        self.requested = []
        self.closed = False
        self.active = 0
        self.max_active = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        self.closed = True

    async def fetch(self, url, settings):
        self.requested.append(str(url))
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(0)
            value = self.pages[str(url)]
            if isinstance(value, Exception):
                raise value
            return value
        finally:
            self.active -= 1


class FixtureSitemaps:
    async def discover(self, homepage, settings):
        return DiscoveryBatch(
            urls=[
                DiscoveredUrl(
                    url="https://example.com/products",
                    normalized_url="https://example.com/products",
                    discovery_source="sitemap",
                    depth=1,
                    depth_basis="sitemap_seed",
                )
            ]
        )


class FixtureRobots:
    def __init__(self, blocked=()):
        self.blocked = blocked

    async def check(self, url):
        if str(url) in self.blocked:
            raise RequestBlocked("robots_disallowed", str(url))
        return 0.0


def page(url, *links, final_url=None, title=None):
    return FetchedPage(
        source_url=url,
        final_url=final_url or url,
        page_title=title,
        crawl_timestamp=datetime.now(UTC),
        crawl_status="success",
        http_status=200,
        raw_html="<main>Example</main>",
        raw_markdown="# Example",
        links=[DiscoveredLink(url=link) for link in links],
    )


def config(**changes):
    return ScraperConfig(request_delay_seconds=(0.0, 0.0), **changes)


async def test_homepage_sitemap_and_links_share_one_deduplicated_budget():
    fetcher = FixtureFetcher(
        {
            "https://example.com/": page("https://example.com/", "https://example.com/pricing"),
            "https://example.com/pricing": page(
                "https://example.com/pricing", "https://example.com/features"
            ),
            "https://example.com/products": page(
                "https://example.com/products", "https://example.com/pricing#plans"
            ),
        }
    )
    crawler = DiscoveryCrawler(fetcher, FixtureSitemaps(), robots_guard=FixtureRobots())
    result = await crawler.run(
        CompetitorInput(homepage_url="https://example.com/"),
        config(max_pages=3, category_keywords={"features": []}),
    )
    assert set(fetcher.requested) == set(fetcher.pages)
    assert len(result.fetched_pages) == 3
    assert fetcher.closed
    features = next(item for item in result.discovered_urls if str(item.url).endswith("features"))
    assert features.disposition == "deferred" and features.reason == "page_limit"


async def test_robots_rejection_does_not_consume_a_page_slot():
    fetcher = FixtureFetcher({"https://example.com/": page("https://example.com/")})
    crawler = DiscoveryCrawler(
        fetcher,
        FixtureSitemaps(),
        robots_guard=FixtureRobots(
            blocked={"https://example.com/products"},
        ),
    )
    result = await crawler.run(CompetitorInput(homepage_url="https://example.com/"), config())
    assert fetcher.requested == ["https://example.com/"]
    assert result.attempted_pages == 1
    products = next(item for item in result.discovered_urls if str(item.url).endswith("products"))
    assert products.disposition == "skipped" and products.reason == "robots_disallowed"


async def test_page_failure_does_not_stop_other_candidates():
    fetcher = FixtureFetcher(
        {
            "https://example.com/": page("https://example.com/", "https://example.com/pricing"),
            "https://example.com/pricing": OSError("fixture network error"),
            "https://example.com/products": page("https://example.com/products"),
        }
    )
    result = await DiscoveryCrawler(fetcher, FixtureSitemaps(), robots_guard=FixtureRobots()).run(
        CompetitorInput(homepage_url="https://example.com/"),
        config(),
    )
    assert len(result.fetched_pages) == 3
    assert sum(item.crawl_status == "failed" for item in result.fetched_pages) == 1
    assert fetcher.closed


async def test_unapproved_redirect_results_do_not_expand_external_content():
    fetcher = FixtureFetcher(
        {
            "https://example.com/": page(
                "https://example.com/",
                "https://other.example/news",
                final_url="https://other.example/pricing",
            ),
            "https://example.com/products": page("https://example.com/products"),
        }
    )
    result = await DiscoveryCrawler(fetcher, FixtureSitemaps(), robots_guard=FixtureRobots()).run(
        CompetitorInput(homepage_url="https://example.com/"),
        config(),
    )
    assert "https://other.example/news" not in {str(item.url) for item in result.discovered_urls}
    assert result.fetched_pages[0].crawl_status == "failed"
    assert result.fetched_pages[0].raw_html == ""


async def test_depth_zero_still_records_sitemap_and_homepage_links():
    fetcher = FixtureFetcher(
        {
            "https://example.com/": page("https://example.com/", "https://example.com/pricing"),
        }
    )
    result = await DiscoveryCrawler(fetcher, FixtureSitemaps(), robots_guard=FixtureRobots()).run(
        CompetitorInput(homepage_url="https://example.com/"),
        config(max_depth=0),
    )
    assert len(result.discovered_urls) == 3
    assert fetcher.requested == ["https://example.com/"]
    assert all(item.reason == "depth_limit" for item in result.discovered_urls[1:])


async def test_per_competitor_overrides_are_resolved_before_traversal():
    fetcher = FixtureFetcher({"https://example.com/": page("https://example.com/")})
    result = await DiscoveryCrawler(fetcher, FixtureSitemaps(), robots_guard=FixtureRobots()).run(
        CompetitorInput(homepage_url="https://example.com/", overrides={"max_pages": 1}),
        config(),
    )
    assert result.attempted_pages == 1
    assert result.effective_config.max_pages == 1


async def test_cancellation_closes_fetcher_and_propagates():
    class BlockingFetcher(FixtureFetcher):
        async def fetch(self, url, settings):
            raise asyncio.CancelledError

    fetcher = BlockingFetcher({})
    with pytest.raises(asyncio.CancelledError):
        await DiscoveryCrawler(fetcher, FixtureSitemaps(), robots_guard=FixtureRobots()).run(
            CompetitorInput(homepage_url="https://example.com/"),
            config(),
        )
    assert fetcher.closed


@pytest.mark.parametrize(
    ("concurrency", "per_domain", "expected"), [(2, 1, 1), (2, 3, 2), (4, 2, 2)]
)
async def test_global_and_per_domain_concurrency_limits(concurrency, per_domain, expected):
    fetcher = FixtureFetcher(
        {
            "https://example.com/": page(
                "https://example.com/", "https://example.com/a", "https://example.com/b"
            ),
            "https://example.com/products": page("https://example.com/products"),
            "https://example.com/a": page("https://example.com/a"),
            "https://example.com/b": page("https://example.com/b"),
        }
    )
    result = await DiscoveryCrawler(fetcher, FixtureSitemaps(), robots_guard=FixtureRobots()).run(
        CompetitorInput(homepage_url="https://example.com/"),
        config(max_concurrency=concurrency, per_domain_concurrency=per_domain, max_pages=4),
    )
    assert result.attempted_pages == 4
    assert fetcher.max_active == expected


async def test_approved_external_host_is_eligible_but_other_subdomains_are_not():
    fetcher = FixtureFetcher(
        {
            "https://example.com/": page(
                "https://example.com/",
                "https://jobs.vendor.example/careers",
                "https://nested.jobs.vendor.example/careers",
            ),
            "https://jobs.vendor.example/careers": page("https://jobs.vendor.example/careers"),
            "https://example.com/products": page("https://example.com/products"),
        }
    )
    result = await DiscoveryCrawler(fetcher, FixtureSitemaps(), robots_guard=FixtureRobots()).run(
        CompetitorInput(homepage_url="https://example.com/"),
        config(allowed_domains=["jobs.vendor.example"]),
    )
    assert "https://jobs.vendor.example/careers" in fetcher.requested
    assert "https://nested.jobs.vendor.example/careers" not in fetcher.requested
    assert any(item.disposition == "external" for item in result.discovered_urls)

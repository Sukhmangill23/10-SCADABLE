import gzip

import httpx
import pytest

from scadable_scraper import ScraperConfig
from scadable_scraper.discovery.sitemaps import BoundedSitemapDiscoverer


def settings(**changes):
    return ScraperConfig(request_delay_seconds=(0.0, 0.0), **changes)


def handler_for(routes, requests):
    def handler(request):
        url = str(request.url)
        requests.append(url)
        value = routes.get(url, (404, b""))
        if isinstance(value, Exception):
            raise value
        status, body, *headers = value
        return httpx.Response(status, content=body, headers=headers[0] if headers else {})

    return handler


async def discover(routes, config=None):
    requests = []
    reader = BoundedSitemapDiscoverer(transport=httpx.MockTransport(handler_for(routes, requests)))
    result = await reader.discover("https://example.com/", config or settings())
    return result, requests


def urlset(*urls):
    entries = "".join(f"<url><loc>{url}</loc></url>" for url in urls)
    return (
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{entries}</urlset>'.encode()
    )


async def test_homepage_sitemap_seeding_follows_robots_directives_and_nested_indexes():
    result, requests = await discover(
        {
            "https://example.com/robots.txt": (
                200,
                b"User-agent: *\nAllow: /\nSitemap: https://example.com/maps/index.xml",
            ),
            "https://example.com/maps/index.xml": (
                200,
                b"<sitemapindex><sitemap><loc>pages.xml</loc></sitemap></sitemapindex>",
            ),
            "https://example.com/maps/pages.xml": (
                200,
                urlset("https://example.com/pricing", "https://example.com/features"),
            ),
        }
    )
    assert {str(item.normalized_url) for item in result.urls} == {
        "https://example.com/pricing",
        "https://example.com/features",
    }
    assert all(item.depth == 1 and item.depth_basis == "sitemap_seed" for item in result.urls)
    assert "https://example.com/pricing" not in requests
    assert "https://example.com/features" not in requests


async def test_missing_robots_allows_standard_sitemap_fallback():
    result, requests = await discover(
        {
            "https://example.com/sitemap.xml": (200, urlset("https://example.com/pricing")),
        }
    )
    assert len(result.urls) == 1
    assert requests[0] == "https://example.com/robots.txt"


async def test_sitemap_urls_outside_scope_are_recorded_without_fetching_pages():
    result, requests = await discover(
        {
            "https://example.com/sitemap.xml": (200, urlset("https://jobs.vendor.example/careers")),
        }
    )
    assert str(result.urls[0].url) == "https://jobs.vendor.example/careers"
    assert not any("jobs.vendor.example" in request for request in requests)


async def test_unapproved_redirect_destination_is_never_requested():
    result, requests = await discover(
        {
            "https://example.com/sitemap.xml": (
                302,
                b"",
                {"location": "https://other.example/map.xml"},
            ),
        }
    )
    assert not any("other.example" in request for request in requests)
    assert any("domain_not_approved" in warning for warning in result.warnings)


async def test_sitemap_disallowed_by_robots_is_not_requested():
    result, requests = await discover(
        {
            "https://example.com/robots.txt": (200, b"User-agent: *\nDisallow: /sitemap"),
        }
    )
    assert requests == ["https://example.com/robots.txt"]
    assert not result.urls
    assert any("robots_disallowed" in warning for warning in result.warnings)


@pytest.mark.parametrize("status", [401, 403, 500, 503])
async def test_robots_failures_do_not_silently_allow_sitemap_requests(status):
    result, requests = await discover({"https://example.com/robots.txt": (status, b"")})
    assert requests == ["https://example.com/robots.txt"]
    assert not result.urls
    assert result.warnings


async def test_cyclic_indexes_are_deduplicated():
    result, requests = await discover(
        {
            "https://example.com/sitemap.xml": (
                200,
                b"<sitemapindex><sitemap><loc>/sitemap.xml</loc></sitemap></sitemapindex>",
            ),
        }
    )
    assert requests.count("https://example.com/sitemap.xml") == 1
    assert not result.urls


async def test_url_limit_is_reported_and_only_unique_candidates_consume_it():
    result, _ = await discover(
        {
            "https://example.com/sitemap.xml": (
                200,
                urlset(
                    "https://example.com/pricing",
                    "https://example.com/pricing#plans",
                    "https://example.com/features",
                    "https://example.com/blog",
                ),
            ),
        },
        settings(max_discovered_urls=2),
    )
    assert len(result.urls) == 2
    assert result.truncated is True


@pytest.mark.parametrize(
    "body",
    [
        b"<invalid",
        b"<html>not a sitemap</html>",
        b'<!DOCTYPE urlset [<!ENTITY x "unsafe">]><urlset><url><loc>&x;</loc></url></urlset>',
    ],
)
async def test_malformed_or_entity_xml_is_reported(body):
    result, _ = await discover({"https://example.com/sitemap.xml": (200, body)})
    assert not result.urls
    assert result.warnings


async def test_gzip_sitemaps_are_supported_with_a_decompressed_size_limit():
    document = gzip.compress(urlset("https://example.com/pricing"))
    result, _ = await discover(
        {
            "https://example.com/robots.txt": (200, b"Sitemap: https://example.com/pages.xml.gz"),
            "https://example.com/pages.xml.gz": (200, document),
        }
    )
    assert len(result.urls) == 1


async def test_oversized_response_is_rejected_with_a_warning():
    result, _ = await discover(
        {"https://example.com/sitemap.xml": (200, b"x" * 500)}, settings(max_sitemap_bytes=128)
    )
    assert not result.urls
    assert any("response_too_large" in warning for warning in result.warnings)


async def test_document_budget_bounds_index_fanout():
    result, requests = await discover(
        {
            "https://example.com/sitemap.xml": (
                200,
                b"<sitemapindex><sitemap><loc>/a.xml</loc></sitemap><sitemap><loc>/b.xml</loc></sitemap></sitemapindex>",
            ),
        },
        settings(max_sitemap_documents=1),
    )
    assert requests == ["https://example.com/robots.txt", "https://example.com/sitemap.xml"]
    assert result.truncated is True


async def test_child_sitemaps_take_priority_over_speculative_root_fallbacks():
    result, requests = await discover(
        {
            "https://example.com/robots.txt": (200, b"Sitemap: https://example.com/maps.xml"),
            "https://example.com/maps.xml": (
                200,
                b"<sitemapindex><sitemap><loc>/pages.xml</loc></sitemap></sitemapindex>",
            ),
            "https://example.com/pages.xml": (200, urlset("https://example.com/pricing")),
        },
        settings(max_sitemap_documents=2),
    )
    assert len(result.urls) == 1
    assert "https://example.com/pages.xml" in requests


async def test_request_budget_includes_robots_and_redirect_hops():
    result, requests = await discover({}, settings(max_sitemap_requests=1))
    assert requests == ["https://example.com/robots.txt"]
    assert result.truncated
    assert any("sitemap_request_limit" in warning for warning in result.warnings)


async def test_index_depth_limit_prevents_fetching_deeper_documents():
    result, requests = await discover(
        {
            "https://example.com/sitemap.xml": (
                200,
                b"<sitemapindex><sitemap><loc>/pages.xml</loc></sitemap></sitemapindex>",
            ),
        },
        settings(max_sitemap_depth=0),
    )
    assert "https://example.com/pages.xml" not in requests
    assert result.truncated


async def test_gzip_expansion_is_bounded_independently_of_compressed_size():
    result, _ = await discover(
        {
            "https://example.com/robots.txt": (200, b"Sitemap: https://example.com/pages.xml.gz"),
            "https://example.com/pages.xml.gz": (200, gzip.compress(b"x" * 5000)),
        },
        settings(max_sitemap_bytes=128),
    )
    assert result.truncated
    assert not result.urls
    assert any("response_too_large" in warning for warning in result.warnings)


async def test_total_discovery_timeout_returns_a_partial_result():
    import asyncio

    async def blocked_handler(request):
        await asyncio.Event().wait()

    reader = BoundedSitemapDiscoverer(transport=httpx.MockTransport(blocked_handler))
    result = await reader.discover("https://example.com/", settings(discovery_timeout_seconds=0.01))
    assert result.truncated
    assert result.warnings == ["sitemap_discovery_timeout"]

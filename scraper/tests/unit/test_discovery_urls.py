"""URL policy contracts: no browser, HTTP client or live website is needed."""

import pytest

from scraper import ScraperConfig
from scraper.discovery.urls import DomainScope, normalize_url


@pytest.mark.parametrize(
    ("raw", "base", "expected"),
    [
        ("/pricing#plans", "https://example.com/", "https://example.com/pricing"),
        ("../features", "https://example.com/products/one", "https://example.com/features"),
        ("HTTPS://EXAMPLE.COM:443/Pricing", None, "https://example.com/Pricing"),
        ("http://example.com:80/", None, "http://example.com/"),
        ("https://example.com:8443/pricing", None, "https://example.com:8443/pricing"),
        ("//www.example.com/blog", "https://example.com/", "https://www.example.com/blog"),
        (
            "/pricing?currency=cad&utm_source=email&gclid=tracking#plans",
            "https://example.com/",
            "https://example.com/pricing?currency=cad",
        ),
        (
            "/products?tag=b&tag=a&page=2",
            "https://example.com/",
            "https://example.com/products?tag=b&tag=a&page=2",
        ),
        ("https://example.com/pricing/", None, "https://example.com/pricing/"),
        ("https://example.com/pricing", None, "https://example.com/pricing"),
    ],
)
def test_normalize_without_losing_meaningful_url_differences(raw, base, expected):
    normalized = normalize_url(raw, base_url=base)
    assert normalized is not None
    assert normalized.normalized == expected
    assert normalized.observed == raw


@pytest.mark.parametrize(
    "raw",
    [
        "mailto:sales@example.com",
        "javascript:void(0)",
        "data:text/html,example",
        "file:///etc/passwd",
        "https://user:secret@example.com/",
        "https://example.com:badport/",
        "https://example.com/\npricing",
        "",
    ],
)
def test_invalid_or_non_web_urls_do_not_enter_the_registry(raw):
    assert normalize_url(raw, base_url="https://example.com/") is None


@pytest.mark.parametrize(
    ("url", "allowed"),
    [
        ("https://example.com/pricing", True),
        ("https://www.example.com/pricing", True),
        ("https://blog.example.com/pricing", False),
        ("https://example.com.attacker.net/pricing", False),
        ("https://otherexample.com/pricing", False),
        ("https://careers.example.com/jobs", True),
        ("https://nested.careers.example.com/jobs", False),
    ],
)
def test_main_host_www_alias_and_explicit_hosts_are_exact(url, allowed):
    scope = DomainScope(
        "https://example.com/",
        ScraperConfig(
            allowed_domains=["careers.example.com"],
        ),
    )
    assert scope.allows(url) is allowed


def test_subdomain_homepage_does_not_imply_approval_of_its_parent_domain():
    scope = DomainScope("https://product.example.com/", ScraperConfig())
    assert scope.allows("https://product.example.com/features")
    assert scope.allows("https://www.product.example.com/features")
    assert not scope.allows("https://example.com/features")
    assert not scope.allows("https://other.example.com/features")

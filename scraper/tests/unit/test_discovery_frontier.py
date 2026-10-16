"""Network-free traversal rules, independent of the pending sitemap implementation."""

from scadable_scraper import ScraperConfig
from scadable_scraper.discovery.traversal import UrlFrontier


def drain(frontier):
    urls = []
    while (record := frontier.pop_next()) is not None:
        urls.append(str(record.normalized_url))
        frontier.complete(str(record.normalized_url), success=True)
    frontier.finalize()
    return urls


def test_best_first_prioritizes_known_relevant_candidates_after_homepage():
    frontier = UrlFrontier("https://example.com/", ScraperConfig(max_pages=3))
    frontier.discover("/misc", parent_url="https://example.com/", depth=1)
    frontier.discover("/pricing", parent_url="https://example.com/", depth=1)
    assert drain(frontier) == [
        "https://example.com/",
        "https://example.com/pricing",
        "https://example.com/misc",
    ]


def test_bfs_visits_shallower_candidates_before_more_relevant_deep_pages():
    frontier = UrlFrontier("https://example.com/", ScraperConfig(strategy="bfs"))
    frontier.discover("/pricing", depth=2)
    frontier.discover("/overview", depth=1)
    assert drain(frontier) == [
        "https://example.com/",
        "https://example.com/overview",
        "https://example.com/pricing",
    ]


def test_duplicates_merge_evidence_without_spending_another_page_slot():
    frontier = UrlFrontier("https://example.com/", ScraperConfig(max_pages=2))
    frontier.discover("/pricing?utm_source=nav", depth=1)
    frontier.discover("/pricing#plans", depth=1, title="Plans")
    assert drain(frontier) == ["https://example.com/", "https://example.com/pricing"]
    pricing = next(
        item for item in frontier.records if str(item.normalized_url).endswith("/pricing")
    )
    assert pricing.discovery_count == 2
    assert len(pricing.evidence) == 2
    assert frontier.attempted_pages == 2


def test_failed_attempts_count_and_boundary_page_links_are_retained():
    frontier = UrlFrontier("https://example.com/", ScraperConfig(max_pages=1))
    homepage = frontier.pop_next()
    frontier.complete(str(homepage.normalized_url), success=False, error="timeout")
    frontier.discover("/pricing", depth=1)
    assert frontier.pop_next() is None
    frontier.finalize()
    assert frontier.attempted_pages == 1
    records = {str(item.normalized_url): item for item in frontier.records}
    assert records["https://example.com/"].disposition == "failed"
    assert records["https://example.com/pricing"].disposition == "deferred"
    assert records["https://example.com/pricing"].reason == "page_limit"


def test_shallower_rediscovery_reopens_a_depth_limited_candidate():
    frontier = UrlFrontier("https://example.com/", ScraperConfig(max_depth=1))
    frontier.discover("/pricing", depth=3)
    frontier.discover("/pricing", depth=1)
    assert drain(frontier) == ["https://example.com/", "https://example.com/pricing"]
    record = frontier.records[1]
    assert record.depth == 1
    assert record.discovery_count == 2


def test_sitemap_depth_one_is_deferred_at_depth_zero():
    frontier = UrlFrontier("https://example.com/", ScraperConfig(max_depth=0))
    frontier.discover("/pricing", depth=1, source="sitemap", depth_basis="sitemap_seed")
    assert drain(frontier) == ["https://example.com/"]
    assert frontier.records[1].reason == "depth_limit"


def test_relevant_unapproved_external_links_are_recorded_but_never_dispatched():
    frontier = UrlFrontier("https://example.com/", ScraperConfig())
    frontier.discover("https://jobs.vendor.example/acme", depth=1, title="Careers")
    frontier.discover("https://blog.example.com/news", depth=1)
    assert drain(frontier) == ["https://example.com/"]
    assert all(item.disposition == "external" for item in frontier.records[1:])


def test_discovery_limit_counts_unique_records_including_skipped_urls():
    frontier = UrlFrontier("https://example.com/", ScraperConfig(max_discovered_urls=2))
    frontier.discover("/login", depth=1)
    frontier.discover("/pricing", depth=1)
    frontier.discover("/login#form", depth=1)
    drain(frontier)
    assert len(frontier.records) == 2
    assert frontier.truncated is True
    assert frontier.records[1].disposition == "skipped"


def test_new_title_can_make_an_opaque_candidate_relevant_without_a_probe():
    frontier = UrlFrontier("https://example.com/", ScraperConfig(minimum_relevance_score=0.01))
    frontier.discover("/a1b2", depth=1)
    frontier.discover("/a1b2", depth=1, title="Pricing plans")
    assert drain(frontier) == ["https://example.com/", "https://example.com/a1b2"]


def test_reserved_candidate_cannot_be_dispatched_twice_before_completion():
    frontier = UrlFrontier("https://example.com/", ScraperConfig())
    first = frontier.pop_next()
    frontier.discover("/#again", depth=0)
    assert first is not None
    assert frontier.pop_next() is None
    assert frontier.attempted_pages == 1


def test_shorter_path_reopens_descendants_without_refetching_their_parent():
    frontier = UrlFrontier("https://example.com/", ScraperConfig(max_depth=2))
    frontier.discover("/features", depth=2)
    homepage = frontier.pop_next()
    frontier.complete(str(homepage.normalized_url), success=True)
    parent = frontier.pop_next()
    frontier.complete(str(parent.normalized_url), success=True)
    frontier.discover("/pricing", parent_url="https://example.com/features", depth=3)
    frontier.discover("/features", depth=1)
    assert drain(frontier) == ["https://example.com/pricing"]
    assert frontier.get("https://example.com/pricing").depth == 2


def test_rediscovery_evidence_has_a_fixed_bound():
    frontier = UrlFrontier("https://example.com/", ScraperConfig())
    for index in range(100):
        frontier.discover(f"/pricing?utm_source={index}", depth=1)
    assert len(frontier.get("https://example.com/pricing").evidence) == 8
    assert frontier.get("https://example.com/pricing").discovery_count == 100
    assert drain(frontier) == ["https://example.com/", "https://example.com/pricing"]

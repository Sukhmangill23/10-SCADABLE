import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from scadable_scraper import ScraperConfig
from scadable_scraper.discovery.http import RequestBlocked


class Guard:
    def __init__(self, deny=()):
        self.deny = deny
        self.seen = []

    async def check(self, url):
        self.seen.append(url)
        if url in self.deny:
            raise RequestBlocked("robots_disallowed", url)
        return 0.0


class FakeCrawler:
    def __init__(self, **kwargs):
        from crawl4ai import CrawlResult

        self.result = CrawlResult.model_validate_json(
            (Path(__file__).parents[1] / "fixtures/crawl4ai_success.json").read_text(
                encoding="utf-8"
            )
        )
        self.hooks = {}
        self.crawler_strategy = SimpleNamespace(set_hook=self.hooks.__setitem__)
        self.closed = False
        self.context = type("Context", (), {})()
        self.context.route = AsyncMock()
        self.page = SimpleNamespace()
        # Real Playwright Page is hashable; use a small hashable stand-in.
        self.page = type("Page", (), {})()
        self.page.main_frame = object()
        self.page.url = "https://example.com/pricing"
        self.page.context = self.context
        self.page.close = AsyncMock()
        self.context.new_cdp_session = AsyncMock(
            return_value=SimpleNamespace(send=AsyncMock(), detach=AsyncMock())
        )
        self.calls = []

    async def start(self):
        return self

    async def close(self):
        self.closed = True

    async def arun(self, url, config):
        self.calls.append((url, config))
        await self.hooks["on_page_context_created"](self.page, self.context, config=config)
        return self.result


async def test_fetch_maps_real_sdk_result_and_closes_browser():
    from scadable_scraper.browser import Crawl4AIFetcher

    runtime = FakeCrawler()
    settings = ScraperConfig(request_delay_seconds=(0.0, 0.0))
    fetcher = Crawl4AIFetcher(
        "https://example.com", settings, Guard(), crawler_factory=lambda **kw: runtime
    )
    async with fetcher:
        page = await fetcher.fetch("https://example.com/pricing", settings)
    assert runtime.closed
    assert page.crawl_status == "success"
    assert page.raw_markdown.startswith("# Pricing")
    assert "$49/month" in page.filtered_markdown
    assert any(str(link.url) == "https://jobs.example.net/example" for link in page.links)
    assert page.page_title == "Example pricing"
    assert page.metadata["description"] == "Example compliance platform plans"
    assert runtime.calls[0][1].check_robots_txt is False


async def test_fetch_robots_refusal_prevents_sdk_navigation():
    from scadable_scraper.browser import Crawl4AIFetcher

    runtime = FakeCrawler()
    settings = ScraperConfig()
    async with Crawl4AIFetcher(
        "https://example.com",
        settings,
        Guard(["https://example.com/pricing"]),
        crawler_factory=lambda **kw: runtime,
    ) as fetcher:
        page = await fetcher.fetch("https://example.com/pricing", settings)
    assert page.crawl_status == "failed"
    assert "robots_disallowed" in page.error_message
    assert runtime.calls == []


async def test_fetch_timeout_and_cancellation_close_owned_page_and_browser():
    from scadable_scraper.browser import Crawl4AIFetcher

    runtime = FakeCrawler()
    original = runtime.arun

    async def hangs(url, config):
        await original(url, config)
        await asyncio.Event().wait()

    runtime.arun = hangs
    settings = ScraperConfig(page_timeout_seconds=0.05, request_delay_seconds=(0.0, 0.0))
    async with Crawl4AIFetcher(
        "https://example.com", settings, Guard(), crawler_factory=lambda **kw: runtime
    ) as fetcher:
        page = await fetcher.fetch("https://example.com/pricing", settings)
        assert page.crawl_status == "failed"
        assert "TimeoutError" in page.error_message
    assert runtime.closed
    assert runtime.page.close.await_count > 0


def test_dynamic_rules_use_first_match_and_inherit_global_defaults():
    from scadable_scraper.browser import select_dynamic_rule

    settings = ScraperConfig(
        dynamic={"max_scroll_steps": 2, "wait_for_css": "main"},
        dynamic_rules=[
            {
                "url_pattern": "*/careers*",
                "scan_full_page": True,
                "load_more_selector": "button.more",
                "max_clicks": 2,
            },
            {"url_pattern": "*", "wait_for_css": "article"},
        ],
    )
    rule = select_dynamic_rule("https://example.com/careers", settings)
    assert rule.max_scroll_steps == 2
    assert rule.wait_for_css == "main"
    assert rule.scan_full_page
    assert rule.max_clicks == 2
    assert rule.load_more_selector == "button.more"


async def test_document_router_blocks_external_redirect_without_requesting_target():
    from scadable_scraper.browser import Crawl4AIFetcher

    settings = ScraperConfig(request_delay_seconds=(0.0, 0.0))
    runtime = FakeCrawler()
    response = SimpleNamespace(
        status=302, headers={"location": "https://outside.test/pricing"}, dispose=AsyncMock()
    )
    request = SimpleNamespace(
        url="https://example.com/pricing",
        resource_type="document",
        method="GET",
        frame=SimpleNamespace(page=runtime.page),
    )
    request.frame = runtime.page.main_frame
    # Frame identity determines whether this is the expected main document.
    runtime.page.main_frame = SimpleNamespace(page=runtime.page)
    request.frame = runtime.page.main_frame
    route = SimpleNamespace(
        request=request,
        fetch=AsyncMock(return_value=response),
        abort=AsyncMock(),
        fulfill=AsyncMock(),
        continue_=AsyncMock(),
    )
    original = runtime.arun

    async def redirect(url, config):
        result = await original(url, config)
        handler = runtime.context.route.call_args.args[1]
        await handler(route)
        return result

    runtime.arun = redirect
    guard = Guard()
    async with Crawl4AIFetcher(
        "https://example.com", settings, guard, crawler_factory=lambda **kw: runtime
    ) as fetcher:
        page = await fetcher.fetch("https://example.com/pricing", settings)
    assert page.crawl_status == "failed"
    assert "domain_not_approved" in page.error_message
    assert all(not url.startswith("https://outside.test") for url in guard.seen)
    assert route.fulfill.await_count == 0
    assert route.fetch.call_args.kwargs["max_redirects"] == 0


async def test_load_more_clicks_are_bounded_and_missing_button_is_normal():
    from scadable_scraper.browser import apply_load_more
    from scadable_scraper.config import DynamicRule

    button = SimpleNamespace(
        count=AsyncMock(return_value=1),
        is_visible=AsyncMock(return_value=True),
        is_enabled=AsyncMock(return_value=True),
        click=AsyncMock(),
    )
    page = SimpleNamespace(locator=lambda selector: SimpleNamespace(first=button))
    rule = DynamicRule(
        url_pattern="*", load_more_selector="button.more", max_clicks=2, scroll_delay_seconds=0.0
    )
    assert await apply_load_more(page, rule) == 2
    button.count.return_value = 0
    assert await apply_load_more(page, rule) == 0


async def test_frameless_popup_document_is_denied_without_callback_error():
    from playwright.async_api import Error

    from scadable_scraper.browser import Crawl4AIFetcher

    class PopupRequest:
        resource_type = "document"

        @property
        def frame(self):
            raise Error("Frame not created yet")

    settings = ScraperConfig()
    fetcher = Crawl4AIFetcher("https://example.com", settings, Guard())
    route = SimpleNamespace(request=PopupRequest(), abort=AsyncMock())
    await fetcher._route(route)
    assert route.abort.await_count == 1


async def test_cancellation_propagates_and_closes_browser_page():
    from scadable_scraper.browser import Crawl4AIFetcher

    runtime = FakeCrawler()
    started = asyncio.Event()
    original = runtime.arun

    async def hangs(url, config):
        await original(url, config)
        started.set()
        await asyncio.Event().wait()

    runtime.arun = hangs
    settings = ScraperConfig()

    async def run():
        async with Crawl4AIFetcher(
            "https://example.com", settings, Guard(), crawler_factory=lambda **kw: runtime
        ) as fetcher:
            await fetcher.fetch("https://example.com/pricing", settings)

    task = asyncio.create_task(run())
    await started.wait()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    else:
        raise AssertionError("Cancellation was swallowed")
    assert runtime.closed
    assert runtime.page.close.await_count > 0


def test_sdk_mapping_keeps_failed_partial_content_and_resolves_relative_links():
    from scadable_scraper.browser import map_sdk_result

    runtime = FakeCrawler()
    result = runtime.result.model_copy(
        update={
            "success": False,
            "status_code": 503,
            "error_message": "Unavailable",
            "links": {
                "internal": [
                    {"href": "../features", "text": "Features"},
                    {"href": "mailto:hi@example.com"},
                ]
            },
        }
    )
    page = map_sdk_result(
        result,
        "https://example.com/pricing",
        final_url="https://example.com/plans/pro",
        metadata={},
    )
    assert page.crawl_status == "failed"
    assert page.http_status == 503
    assert page.error_message == "Unavailable"
    assert "$49/month" in page.raw_markdown
    assert [str(link.url) for link in page.links] == ["https://example.com/features"]


async def test_constructor_failure_releases_temporary_browser_directory(tmp_path, monkeypatch):
    from tempfile import TemporaryDirectory

    from scadable_scraper import browser

    directory = tmp_path / "browser-temp"
    directory.mkdir()
    monkeypatch.setattr(
        browser, "TemporaryDirectory", lambda **kw: TemporaryDirectory(dir=directory)
    )

    def broken(**kw):
        raise OSError("Constructor failed")

    fetcher = browser.Crawl4AIFetcher(
        "https://example.com", ScraperConfig(), Guard(), crawler_factory=broken
    )
    with pytest.raises(OSError):
        async with fetcher:
            pass
    assert list(directory.iterdir()) == []


async def test_shared_redirect_destination_limits_render_concurrency():
    from scadable_scraper.browser import Crawl4AIFetcher
    from scadable_scraper.limits import HostLimiter

    settings = ScraperConfig(allowed_domains=["two.example"], request_delay_seconds=(0.0, 0.0))
    limiter = HostLimiter(1)
    active = peak = 0

    async def collect(homepage):
        runtime = FakeCrawler()
        fetcher = Crawl4AIFetcher(
            homepage, settings, Guard(), crawler_factory=lambda **kw: runtime, host_limiter=limiter
        )
        original = runtime.arun

        async def render(url, config):
            nonlocal active, peak
            result = await original(url, config)
            if url == "https://one.example/":
                fetcher._current.get().redirect = "https://two.example/pricing"
            else:
                active += 1
                peak = max(peak, active)
                try:
                    await asyncio.sleep(0.03)
                finally:
                    active -= 1
            return result.model_copy(update={"redirected_url": url})

        runtime.arun = render
        async with fetcher:
            return await fetcher.fetch(homepage, settings)

    pages = await asyncio.gather(collect("https://one.example/"), collect("https://two.example/"))
    assert all(page.crawl_status == "success" for page in pages)
    assert peak == 1

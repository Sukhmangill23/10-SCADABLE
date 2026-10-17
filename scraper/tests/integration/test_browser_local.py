"""Opt-in real Chromium checks. Every HTTP request uses a loopback fixture server."""

import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from scraper import ScraperConfig
from scraper.browser import Crawl4AIFetcher
from scraper.discovery.http import GuardedHttpClient

pytestmark = [
    pytest.mark.browser,
    pytest.mark.skipif(
        os.getenv("SCRAPER_BROWSER_TESTS") != "1",
        reason="Set SCRAPER_BROWSER_TESTS=1 for loopback Chromium checks",
    ),
]


@pytest.fixture
def website():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append((self.headers.get("Host"), self.path))
            if self.path == "/robots.txt":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"User-agent: *\nAllow: /\nDisallow: /private\n")
                return
            paths = [path for _, path in requests]
            if self.path == "/permanent" or (
                self.path == "/transient" and paths.count("/transient") < 3
            ):
                self.send_response(403 if self.path == "/permanent" else 503)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<main><h1>Temporary fixture failure</h1></main>")
                return
            redirects = {
                "/redirect": "/pricing",
                "/external": f"http://localhost:{self.server.server_port}/forbidden",
                "/robots-redirect": "/private",
                "/loop": "/loop",
            }
            if self.path in redirects:
                self.send_response(302)
                self.send_header("Location", redirects[self.path])
                self.end_headers()
                return
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "application/javascript"
                if self.path == "/resource.js"
                else "text/html; charset=utf-8",
            )
            self.end_headers()
            if self.path == "/resource.js":
                body = (
                    "document.getElementById('external').textContent='Third party script rendered';"
                )
            else:
                body = f"""<!doctype html><html lang="en"><head><title>Fixture pricing</title>
                <meta name="description" content="Competitive plans"></head><body>
                <main><h1>Pricing</h1><div id="external"></div>
                <script src="http://localhost:{self.server.server_port}/resource.js"></script>
                <div id="plans">Starter $49</div><button id="more">Load more</button>
                <a href="/products">Products</a><iframe src="/embedded"></iframe></main>
                <a href="/transient">Pricing plans</a><a href="/permanent">News</a>
                <script>let clicks=0; document.querySelector('#more').onclick=()=>{{
                document.querySelector('#plans').insertAdjacentHTML('beforeend','<p>Pro $99</p>');
                if(++clicks===2) document.querySelector('#more').remove();}};
                setTimeout(()=>{{document.querySelector('main').id='ready';}},50);
                window.open('/popup');</script></body></html>"""
            self.wfile.write(body.encode())

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


async def test_render_redirect_wait_load_more_links_and_external_script(website):
    base, requests = website
    settings = ScraperConfig(
        request_delay_seconds=(0.0, 0.0),
        dynamic_rules=[
            {
                "url_pattern": "*/pricing",
                "wait_for_css": "#ready",
                "load_more_selector": "#more",
                "max_clicks": 3,
                "scroll_delay_seconds": 0.05,
            }
        ],
    )

    class LoopbackFetcher(Crawl4AIFetcher):
        async def _on_page(self, page, context, **kwargs):
            # Chromium treats fulfilled documents as unknown address space. This
            # permission is confined to the loopback test, never production.
            await context.grant_permissions(["local-network-access"])
            return await super()._on_page(page, context, **kwargs)

    async with GuardedHttpClient(base, settings) as guard:
        async with LoopbackFetcher(base, settings, guard) as fetcher:
            page = await fetcher.fetch(base + "/redirect", settings)
    assert page.crawl_status == "success", page.error_message
    assert str(page.source_url) == base + "/redirect"
    assert str(page.final_url) == base + "/pricing"
    assert "Starter $49" in page.raw_markdown
    assert page.raw_markdown.count("Pro $99") == 2
    assert "Third party script rendered" in page.raw_markdown
    assert page.filtered_markdown is not None
    assert page.metadata["load_more_clicks"] == 2
    assert page.metadata["redirect_chain"] == [base + "/pricing"]
    assert any(str(link.url) == base + "/products" for link in page.links)
    paths = [path for _, path in requests]
    assert paths.count("/redirect") == paths.count("/pricing") == 1
    assert "/embedded" not in paths
    assert "/popup" not in paths


@pytest.mark.parametrize(
    "path,reason,forbidden",
    [
        ("/external", "domain_not_approved", "/forbidden"),
        ("/robots-redirect", "robots_disallowed", "/private"),
        ("/loop", "redirect_limit", None),
    ],
)
async def test_redirects_are_blocked_before_destination_request(website, path, reason, forbidden):
    base, requests = website
    settings = ScraperConfig(max_redirects=2, request_delay_seconds=(0.0, 0.0))
    async with GuardedHttpClient(base, settings) as guard:
        async with Crawl4AIFetcher(base, settings, guard) as fetcher:
            page = await fetcher.fetch(base + path, settings)
    assert page.crawl_status == "failed"
    assert reason in page.error_message
    paths = [path for _, path in requests]
    assert forbidden is None or forbidden not in paths
    if path == "/loop":
        assert paths.count("/loop") == 3


def test_real_cli_pipeline_writes_parseable_jsonl(website, tmp_path):
    base, requests = website
    config = tmp_path / "local.toml"
    config.write_text(
        "[global]\nmax_pages=2\nmax_depth=1\nrequest_delay_seconds=[0.0,0.0]\n", encoding="utf-8"
    )
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "scraper",
            base,
            "--config",
            str(config),
            "--format",
            "jsonl",
            "--output",
            "-",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=45,
    )
    assert process.returncode == 0, process.stderr
    records = [json.loads(line) for line in process.stdout.splitlines()]
    assert [record["record_type"] for record in records] == ["page", "page", "competitor_summary"]
    assert records[-1]["result"]["summary"]["successful"] == 2
    assert all("Starter $49" in record["page"]["raw_markdown"] for record in records[:2])
    assert "Starting" in process.stderr
    assert "/embedded" not in [path for _, path in requests]


async def test_real_browser_retries_and_partial_results_preserve_page_budget(website):
    from scraper import CompetitorInput
    from scraper.service import CompetitorScraper

    base, requests = website
    settings = ScraperConfig(
        max_pages=4, max_depth=1, max_backoff_seconds=0.01, request_delay_seconds=(0.0, 0.0)
    )
    result = await CompetitorScraper().crawl(CompetitorInput(homepage_url=base), settings)
    assert result.run_status == "partial"
    assert len(result.pages) == 4
    assert result.summary.successful == 3
    assert result.summary.failed == 1
    transient = next(page for page in result.pages if str(page.source_url).endswith("/transient"))
    assert transient.attempt_count == 3
    assert transient.crawl_status == "success"
    assert "Starter $49" in transient.raw_markdown
    permanent = next(page for page in result.pages if str(page.source_url).endswith("/permanent"))
    assert permanent.attempt_count == 1
    assert permanent.http_status == 403
    paths = [path for _, path in requests]
    assert paths.count("/transient") == 3
    assert paths.count("/permanent") == 1


async def test_real_sdk_wrapped_selector_timeouts_are_retried(website):
    from scraper import CompetitorInput
    from scraper.service import CompetitorScraper

    base, requests = website
    settings = ScraperConfig(
        max_pages=1,
        max_depth=0,
        max_backoff_seconds=0.01,
        request_delay_seconds=(0.0, 0.0),
        dynamic={"wait_for_css": "#never-present", "wait_timeout_seconds": 0.02},
    )
    result = await CompetitorScraper().crawl(CompetitorInput(homepage_url=base), settings)
    assert result.run_status == "failed"
    assert len(result.pages) == 1
    page = result.pages[0]
    assert page.attempt_count == 3
    assert page.metadata["crawl_diagnostics"]["stop_reason"] == "retries_exhausted"
    assert {
        attempt["failure_kind"] for attempt in page.metadata["crawl_diagnostics"]["attempts"]
    } == {"timeout"}
    assert [path for _, path in requests].count("/") == 3

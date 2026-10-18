"""Opt-in real Chromium checks. Every HTTP request uses a loopback fixture server."""

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
        selection={"mode": "structural"},
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
    settings = ScraperConfig(
        selection={"mode": "structural"}, max_redirects=2, request_delay_seconds=(0.0, 0.0)
    )
    async with GuardedHttpClient(base, settings) as guard:
        async with Crawl4AIFetcher(base, settings, guard) as fetcher:
            page = await fetcher.fetch(base + path, settings)
    assert page.crawl_status == "failed"
    assert reason in page.error_message
    paths = [path for _, path in requests]
    assert forbidden is None or forbidden not in paths
    if path == "/loop":
        assert paths.count("/loop") == 3


def test_real_cli_pipeline_writes_markdown_and_summary(website, tmp_path):
    base, requests = website
    config = tmp_path / "local.toml"
    config.write_text(
        "[global]\nmax_pages=2\nmax_depth=1\nrequest_delay_seconds=[0.0,0.0]\n"
        '[global.selection]\nmode="structural"\n',
        encoding="utf-8",
    )
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "scraper",
            base,
            "--config",
            str(config),
            "--output",
            str(tmp_path / "exports"),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=45,
    )
    assert process.returncode == 0, process.stderr
    from scraper.models import CrawlExportSummary

    indexes = list((tmp_path / "exports").rglob("crawl_summary.json"))
    assert len(indexes) == 1
    summary = CrawlExportSummary.model_validate_json(indexes[0].read_text(encoding="utf-8"))
    assert summary.counts.successful == 2
    assert len(summary.pages) == 2
    assert all(
        "Starter $49" in (indexes[0].parent / page.markdown_file).read_text(encoding="utf-8")
        for page in summary.pages
    )
    assert all(page.duration_seconds is not None for page in summary.pages)
    assert summary.counts.deferred > 0
    assert any(page.discovered_from for page in summary.pages)
    assert "raw_markdown" not in indexes[0].read_text(encoding="utf-8")
    assert "Starting" in process.stderr
    assert "/embedded" not in [path for _, path in requests]


async def test_real_browser_retries_and_partial_results_preserve_page_budget(website):
    from scraper import CompetitorInput
    from scraper.service import CompetitorScraper

    base, requests = website
    settings = ScraperConfig(
        selection={"mode": "structural"},
        max_pages=4,
        max_depth=1,
        max_backoff_seconds=0.01,
        request_delay_seconds=(0.0, 0.0),
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
        selection={"mode": "structural"},
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


async def test_real_browser_with_mock_decisions_publishes_context_assessment_and_trace(
    website, tmp_path, monkeypatch
):
    import json

    import httpx2
    from openai import AsyncOpenAI

    from scraper import CompetitorInput
    from scraper.decisions import OpenAIDecisionProvider
    from scraper.output import competitor_directory, export_competitor
    from scraper.service import CompetitorScraper

    base, requests = website
    calls = []
    clients = []
    monkeypatch.setenv("OPENAI_API_KEY", "test-not-a-real-key")

    def handle(request):
        assert str(request.url) == "https://api.openai.com/v1/decisions"
        payload = json.loads(request.content)
        calls.append(payload)
        evidence = json.loads(payload["input"])
        if "candidates" in evidence:
            answers = [
                {
                    "name": f"candidate_{i}",
                    "type": "score",
                    "confidence": 0.9,
                    "score": 3 if item["url"].endswith("/products") else 0,
                }
                for i, item in enumerate(evidence["candidates"])
            ]
        else:
            answers = [
                {"name": name, "type": "score", "confidence": 0.9, "score": 3}
                for name in ("usefulness", "novelty")
            ] + [{"name": "category", "type": "choice", "confidence": 0.9, "choice": "pricing"}]
        return httpx2.Response(
            200,
            json={
                "answers": answers,
                "model": "gpt-6-luna",
                "usage": {"input_tokens": 100},
            },
        )

    def factory(competitor, settings, limiter):
        def client_factory(**kwargs):
            client = AsyncOpenAI(
                **kwargs, http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handle))
            )
            clients.append(client)
            return client

        return OpenAIDecisionProvider(
            settings.selection, request_limiter=limiter, client_factory=client_factory
        )

    result = await CompetitorScraper(decision_provider_factory=factory).crawl(
        CompetitorInput(homepage_url=base),
        ScraperConfig(
            max_pages=2,
            max_depth=1,
            max_concurrency=1,
            request_delay_seconds=(0.0, 0.0),
            selection={"trace_enabled": True},
        ),
    )
    assert result.run_status == "success"
    assert str(result.pages[1].source_url) == base + "/products"
    candidates = [
        json.loads(call["input"])["candidates"]
        for call in calls
        if "candidates" in json.loads(call["input"])
    ]
    product = next(item for item in candidates[0] if item["url"].endswith("/products"))
    assert product["observations"][0]["location"] == "main_content"
    assert product["observations"][0]["heading"] == "Pricing"
    summary = export_competitor(result, tmp_path)
    folder = tmp_path / competitor_directory(base)
    assert summary.pages[1].selection.assessment_available
    assert summary.pages[1].category == "pricing"
    assert summary.decision_usage.reported_input_tokens == len(calls) * 100
    assert (folder / summary.decision_trace_file).is_file()
    assert all(client.is_closed() for client in clients)
    assert "/embedded" not in [path for _, path in requests]

"""Opt-in subprocess checks with real Chromium, loopback HTTP, and offline analysis."""

import asyncio
import os
import subprocess
import sys
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from scraper.browser import Crawl4AIFetcher
from scraper.service import CompetitorScraper

from llm.pipeline import run_pipeline
from scraper import CompetitorInput, ScraperConfig
from scraper.output import competitor_directory
from tests.helpers import StubAnalyzer

pytestmark = pytest.mark.skipif(
    os.getenv("SCRAPER_BROWSER_TESTS") != "1",
    reason="Set SCRAPER_BROWSER_TESTS=1 for loopback Chromium pipeline checks",
)


async def run_browser_fixture(mode, output):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            assert self.path.startswith("/")
            self.send_response(200)
            self.end_headers()
            if self.path == "/robots.txt":
                body = "User-agent: *\nAllow: /\n"
            elif self.path == "/sitemap.xml":
                body = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>'
            else:
                body = (
                    "<html><head><title>Fixture company</title></head><body><main>"
                    "<h1>Evidence platform</h1><p>Pro plan costs $49 per month.</p>"
                    '<a href="/pricing">Pricing</a></main></body></html>'
                )
            self.wfile.write(body.encode())

        def log_message(self, *_):
            pass

    with ExitStack() as resources:
        companies = []
        for number in range(3):
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            resources.callback(thread.join, timeout=2)
            resources.callback(server.server_close)
            resources.callback(server.shutdown)
            companies.append(
                CompetitorInput(
                    homepage_url=f"http://127.0.0.1:{server.server_port}/",
                    name=f"Fixture {number}",
                )
            )
        analyzer = StubAnalyzer()
        starting = asyncio.Event()

        class StartingFetcher(Crawl4AIFetcher):
            async def __aenter__(self):
                starting.set()
                return await super().__aenter__()

        service = CompetitorScraper(
            fetcher_factory=(
                lambda company, settings, guard: StartingFetcher(
                    str(company.homepage_url), settings, guard
                )
            )
            if mode == "cancel"
            else None
        )
        if mode == "missing":
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(output / "missing-browsers")
        task = asyncio.create_task(
            run_pipeline(
                companies,
                scraper=service,
                scraper_settings=ScraperConfig(
                    selection={"mode": "structural"},
                    max_pages=2,
                    max_concurrent_competitors=3,
                    max_sitemap_documents=1,
                    request_delay_seconds=(0.0, 0.0),
                    page_timeout_seconds=10,
                ),
                output_directory=output,
                analyzer=analyzer,
            )
        )
        if mode == "cancel":
            await starting.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        elif mode == "missing":
            with pytest.raises(ValueError, match="Chromium is not installed") as caught:
                await task
            assert sys.executable in str(caught.value)
            assert "-m playwright install chromium" in str(caught.value)
            assert str(output / "missing-browsers") in str(caught.value)
            assert analyzer.calls == []
            assert list(output.glob("*/crawl_summary.json"))
        else:
            results = await task
            assert len(results) == 3
            assert len(analyzer.inputs) == 3
            for data in analyzer.inputs:
                assert data.crawl_summary.counts.successful == 2
                bundle = output / competitor_directory(
                    str(data.crawl_summary.homepage_url)
                )
                for page in data.pages:
                    assert "$49" in page.markdown
                    assert (bundle / page.source.markdown_file).read_text(
                        encoding="utf-8"
                    ) == page.markdown
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        assert not pending, [t.get_coro().__qualname__ for t in pending]


@pytest.mark.parametrize("mode", ["success", "missing", "cancel"])
def test_real_browser_pipeline_and_failure_shutdown(tmp_path, mode):
    environment = dict(
        os.environ, PYTHON_DOTENV_DISABLED="1", CRAWL4AI_NO_CLOUD_NOTICE="1"
    )
    for name in (
        "OPENAI_API_KEY",
        "PLAYWRIGHT_BROWSERS_PATH",
        "CRAWL4_AI_BASE_DIRECTORY",
    ):
        environment.pop(name, None)
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            (
                "import asyncio, sys; from pathlib import Path; "
                "from tests.test_research_browser import run_browser_fixture; "
                "asyncio.run(run_browser_fixture(sys.argv[1], Path(sys.argv[2])))"
            ),
            mode,
            str(tmp_path / "run"),
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for message in ("Event loop is closed", "Task was destroyed", "unclosed transport"):
        assert message not in result.stderr

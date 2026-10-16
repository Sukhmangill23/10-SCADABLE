import json
import os
import subprocess
import sys

import pytest

from scadable_scraper import CompetitorCrawlResult
from scadable_scraper.types import utc_now


class FixtureService:
    observed = []

    async def crawl_many(self, competitors, global_settings, *, cli_overrides):
        from scadable_scraper.config import resolve_config

        self.observed[:] = competitors
        for competitor in competitors:
            now = utc_now()
            yield CompetitorCrawlResult(
                competitor_name=competitor.display_name,
                homepage_url=competitor.homepage_url,
                started_at=now,
                finished_at=now,
                run_status="success",
                completion_reason="completed",
                effective_config=resolve_config(
                    global_settings, competitor.overrides, cli_overrides
                ),
            )


def test_cli_writes_multiple_competitors_to_json_without_browser(tmp_path, monkeypatch):
    from scadable_scraper import cli

    monkeypatch.setattr(cli, "CompetitorScraper", FixtureService)
    target = tmp_path / "results.json"
    assert (
        cli.main(
            [
                "https://one.example",
                "https://two.example",
                "--output",
                str(target),
                "--max-pages",
                "3",
            ]
        )
        == 0
    )
    data = json.loads(target.read_text(encoding="utf-8"))
    assert [r["homepage_url"] for r in data["results"]] == [
        "https://one.example/",
        "https://two.example/",
    ]
    assert all(r["effective_config"]["max_pages"] == 3 for r in data["results"])


def test_cli_config_matching_preserves_overrides_and_selects_requested_homepages(
    tmp_path, monkeypatch
):
    from scadable_scraper import cli

    monkeypatch.setattr(cli, "CompetitorScraper", FixtureService)
    config = tmp_path / "config.toml"
    config.write_text(
        '[global]\nmax_pages=10\n[[competitors]]\nhomepage_url="https://one.example/"\nname="One"\n[competitors.overrides]\nmax_pages=2\n[[competitors]]\nhomepage_url="https://two.example/"\n',
        encoding="utf-8",
    )
    target = tmp_path / "results.json"
    assert cli.main(["https://one.example", "--config", str(config), "--output", str(target)]) == 0
    result = json.loads(target.read_text(encoding="utf-8"))["results"]
    assert len(result) == 1
    assert result[0]["competitor_name"] == "One"
    assert result[0]["effective_config"]["max_pages"] == 2


def test_cli_jsonl_stdout_remains_machine_readable(monkeypatch, capsys):
    from scadable_scraper import cli

    monkeypatch.setattr(cli, "CompetitorScraper", FixtureService)
    assert cli.main(["https://one.example", "--output", "-", "--format", "jsonl"]) == 0
    records = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert records[0]["record_type"] == "competitor_summary"


@pytest.mark.parametrize(
    "args", [[], ["https://example.com/pricing"], ["https://example.com", "--max-pages", "0"]]
)
def test_invalid_input_exits_before_browser_start(args, capsys):
    from scadable_scraper.cli import main

    assert main(args) == 2
    assert capsys.readouterr().err


def test_existing_output_is_not_overwritten(tmp_path, monkeypatch):
    from scadable_scraper import cli

    monkeypatch.setattr(cli, "CompetitorScraper", FixtureService)
    target = tmp_path / "results.json"
    target.write_text("existing", encoding="utf-8")
    assert cli.main(["https://example.com", "--output", str(target)]) == 2
    assert target.read_text(encoding="utf-8") == "existing"


@pytest.mark.parametrize("format", ["json", "jsonl"])
def test_redirected_stdout_is_utf8_under_windows_legacy_encoding(format, tmp_path):
    code = """
from scadable_scraper import cli, CompetitorCrawlResult, ScrapedPage
from scadable_scraper.types import utc_now
class Service:
    async def crawl_many(self, *args, **kwargs):
        now = utc_now()
        page = ScrapedPage(
            competitor_name="Example", homepage_url="https://example.com",
            source_url="https://example.com", crawl_timestamp=now,
            crawl_status="success", raw_markdown="\\u4e2d\\u6587 \\u20ac49")
        yield CompetitorCrawlResult(
            competitor_name="Example", homepage_url="https://example.com",
            started_at=now, finished_at=now, run_status="success",
            completion_reason="completed", pages=[page])
cli.CompetitorScraper = Service
raise SystemExit(cli.main(["https://example.com", "--output", "-", "--format", FORMAT]))
""".replace("FORMAT", repr(format))
    process = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env=os.environ | {"PYTHONIOENCODING": "cp1252"},
        capture_output=True,
        timeout=15,
    )
    assert process.returncode == 0, process.stderr
    output = process.stdout.decode("utf-8")
    if format == "json":
        assert json.loads(output)["results"][0]["pages"][0]["raw_markdown"] == "中文 €49"
    else:
        assert json.loads(output.splitlines()[0])["page"]["raw_markdown"] == "中文 €49"

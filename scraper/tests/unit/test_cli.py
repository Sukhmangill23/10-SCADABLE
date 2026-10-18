import json
import os
import subprocess
import sys

import pytest

from scraper import CompetitorCrawlResult, ScrapedPage
from scraper.types import utc_now


class FixtureService:
    observed = []
    closed = False

    async def crawl_many(self, competitors, global_settings, *, cli_overrides):
        from scraper.config import resolve_config

        self.observed[:] = competitors
        try:
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
                    pages=[
                        ScrapedPage(
                            competitor_name=competitor.display_name,
                            homepage_url=competitor.homepage_url,
                            source_url=competitor.homepage_url,
                            crawl_timestamp=now,
                            crawl_status="success",
                            raw_markdown="# Raw content",
                            cleaned_markdown="# Home\n\nPro €49",
                        )
                    ],
                )
        finally:
            FixtureService.closed = True


def read_summary(root, hostname="one.example"):
    return json.loads((root / hostname / "crawl_summary.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("explicit", [False, True])
def test_cli_loads_dotenv_before_starting_service(tmp_path, monkeypatch, explicit):
    from scraper import cli

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED", raising=False)
    # Ensure dotenv mutation is restored by monkeypatch at teardown.
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.delenv("OPENAI_API_KEY")
    env_file = tmp_path / ("custom.env" if explicit else ".env")
    env_file.write_text("OPENAI_API_KEY=cli-fixture-key\n", encoding="utf-8")

    class DotenvService(FixtureService):
        async def crawl_many(self, *args, **kwargs):
            assert os.environ["OPENAI_API_KEY"] == "cli-fixture-key"
            async for result in super().crawl_many(*args, **kwargs):
                yield result

    monkeypatch.setattr(cli, "CompetitorScraper", DotenvService)
    options = ["--env-file", str(env_file)] if explicit else []
    assert cli.main(["https://one.example", "--output", str(tmp_path / "out"), *options]) == 0


def test_cli_rejects_missing_explicit_environment_file_before_crawler(
    tmp_path, monkeypatch, capsys
):
    from scraper import cli

    def forbidden():
        raise AssertionError("Must not create a crawler")

    monkeypatch.setattr(cli, "CompetitorScraper", forbidden)
    assert cli.main(["https://one.example", "--env-file", str(tmp_path / "missing.env")]) == 2
    assert "Environment file not found" in capsys.readouterr().err


def test_cli_exports_multiple_competitors_without_browser(tmp_path, monkeypatch):
    from scraper import cli

    monkeypatch.setattr(cli, "CompetitorScraper", FixtureService)
    assert (
        cli.main(
            [
                "https://one.example",
                "https://two.example",
                "--output",
                str(tmp_path),
                "--max-pages",
                "3",
            ]
        )
        == 0
    )
    for hostname in ("one.example", "two.example"):
        summary = read_summary(tmp_path, hostname)
        assert summary["homepage_url"] == f"https://{hostname}/"
        assert summary["counts"]["successful"] == 1
        assert (tmp_path / hostname / "pages/index.md").read_text(
            encoding="utf-8"
        ) == "# Home\n\nPro €49"
        assert "raw_markdown" not in str(summary)
    assert FixtureService.closed


def test_cli_config_matching_preserves_overrides_and_selection(tmp_path, monkeypatch):
    from scraper import cli

    monkeypatch.setattr(cli, "CompetitorScraper", FixtureService)
    config = tmp_path / "config.toml"
    config.write_text(
        '[global]\nmax_pages=10\n[[competitors]]\nhomepage_url="https://one.example/"\nname="One"\n[competitors.overrides]\nmax_pages=2\n[[competitors]]\nhomepage_url="https://two.example/"\n',
        encoding="utf-8",
    )
    assert (
        cli.main(
            ["https://one.example", "--config", str(config), "--output", str(tmp_path / "exports")]
        )
        == 0
    )
    assert read_summary(tmp_path / "exports")["competitor_name"] == "One"
    assert FixtureService.observed[0].overrides.max_pages == 2
    assert not (tmp_path / "exports/two.example").exists()


def test_cli_default_output_is_a_directory(tmp_path, monkeypatch):
    from scraper import cli

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "CompetitorScraper", FixtureService)
    assert cli.main(["https://one.example"]) == 0
    assert read_summary(tmp_path / "output")["schema_version"] == "2.1"


def test_selection_cli_overrides_are_sparse_and_preserve_nested_precedence(tmp_path):
    from scraper.cli import _inputs, _parser
    from scraper.config import resolve_config

    config = tmp_path / "config.toml"
    config.write_text(
        '[global.selection]\nmode="llm"\nbudget_usd=0.02\ntrace_enabled=true\n'
        'max_retries=1\n[[competitors]]\nhomepage_url="https://one.example/"\n'
        '[competitors.overrides.selection]\nobjective="Research customer evidence"\n',
        encoding="utf-8",
    )
    args = _parser().parse_args(
        [
            "--config",
            str(config),
            "--selection-mode",
            "structural",
            "--decision-budget-usd",
            "0.01",
            "--no-decision-trace",
        ]
    )
    competitors, project, overrides = _inputs(args)
    effective = resolve_config(project.global_settings, competitors[0].overrides, overrides)
    assert effective.selection.mode == "structural"
    assert effective.selection.budget_usd == 0.01
    assert effective.selection.trace_enabled is False
    assert effective.selection.objective == "Research customer evidence"
    assert effective.selection.max_retries == 1
    assert overrides.model_dump(exclude_unset=True) == {
        "selection": {"mode": "structural", "budget_usd": 0.01, "trace_enabled": False},
    }
    _, _, omitted = _inputs(_parser().parse_args(["--config", str(config)]))
    assert omitted.model_dump(exclude_unset=True) == {}


def test_cli_research_objective_and_trace_reach_exporter(tmp_path, monkeypatch):
    from scraper import cli

    monkeypatch.setattr(cli, "CompetitorScraper", FixtureService)
    assert (
        cli.main(
            [
                "https://one.example",
                "--output",
                str(tmp_path),
                "--research-objective",
                "Company expansion and customer wins",
                "--decision-trace",
                "--selection-mode",
                "structural",
            ]
        )
        == 0
    )
    assert read_summary(tmp_path)["decision_trace_file"] == "decisions.jsonl"
    assert (tmp_path / "one.example/decisions.jsonl").read_bytes() == b""


@pytest.mark.parametrize("allowance", ["-0.1", "nan", "inf"])
def test_invalid_decision_allowance_fails_before_crawler(allowance, capsys):
    from scraper import cli

    assert cli.main(["https://one.example", "--decision-budget-usd", allowance]) == 2
    assert "budget_usd" in capsys.readouterr().err


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["https://example.com/pricing"],
        ["https://example.com", "--max-pages", "0"],
        ["https://example.com", "--output", "-"],
    ],
)
def test_invalid_input_exits_before_starting_browser(args, capsys):
    from scraper.cli import main

    assert main(args) == 2
    assert capsys.readouterr().err


@pytest.mark.parametrize("option", [["--format", "jsonl"], ["--format", "json"], ["--overwrite"]])
def test_obsolete_file_output_flags_are_rejected(option):
    from scraper.cli import main

    with pytest.raises(SystemExit) as error:
        main(["https://example.com", *option])
    assert error.value.code == 2


def test_existing_competitor_directory_is_rejected_before_any_crawl(tmp_path, monkeypatch):
    from scraper import cli

    target = tmp_path / "two.example"
    target.mkdir()
    (target / "notes.txt").write_text("user notes")
    FixtureService.observed.clear()
    monkeypatch.setattr(cli, "CompetitorScraper", FixtureService)
    assert cli.main(["https://one.example", "https://two.example", "--output", str(tmp_path)]) == 2
    assert not FixtureService.observed
    assert not (tmp_path / "one.example").exists()
    assert (target / "notes.txt").read_text() == "user notes"


def test_file_output_root_is_rejected_without_overwriting(tmp_path, monkeypatch):
    from scraper import cli

    target = tmp_path / "old.json"
    target.write_text("old crawl")
    monkeypatch.setattr(cli, "CompetitorScraper", FixtureService)
    assert cli.main(["https://one.example", "--output", str(target)]) == 2
    assert target.read_text() == "old crawl"


def test_interruption_retains_completed_competitor(tmp_path, monkeypatch):
    from scraper import cli

    class Interrupted(FixtureService):
        async def crawl_many(self, *args, **kwargs):
            async for result in super().crawl_many(*args, **kwargs):
                yield result
                raise KeyboardInterrupt

    monkeypatch.setattr(cli, "CompetitorScraper", Interrupted)
    assert (
        cli.main(["https://one.example", "https://two.example", "--output", str(tmp_path)]) == 130
    )
    assert read_summary(tmp_path)["counts"]["successful"] == 1
    assert not (tmp_path / "two.example").exists()


def test_write_failure_closes_workers_and_preserves_unrelated_output(tmp_path, monkeypatch):
    from scraper import cli

    old = tmp_path / "old.jsonl"
    old.write_text("old results")
    FixtureService.closed = False
    monkeypatch.setattr(cli, "CompetitorScraper", FixtureService)

    def broken(*args):
        raise OSError("disk full")

    monkeypatch.setattr(cli, "export_competitor", broken)
    assert cli.main(["https://one.example", "--output", str(tmp_path)]) == 2
    assert FixtureService.closed
    assert old.read_text() == "old results"


def test_export_is_utf8_under_windows_legacy_console_encoding(tmp_path):
    code = """
from scraper import cli, CompetitorCrawlResult, ScrapedPage
from scraper.types import utc_now
class Service:
    async def crawl_many(self, *args, **kwargs):
        now = utc_now()
        page = ScrapedPage(competitor_name="Example", homepage_url="https://example.com",
            source_url="https://example.com", crawl_timestamp=now, crawl_status="success",
            raw_markdown="\\u4e2d\\u6587 \\u20ac49", cleaned_markdown="\\u4e2d\\u6587 \\u20ac49")
        yield CompetitorCrawlResult(competitor_name="Example", homepage_url="https://example.com",
            started_at=now, finished_at=now, run_status="success",
            completion_reason="completed", pages=[page])
cli.CompetitorScraper = Service
raise SystemExit(cli.main(["https://example.com", "--output", TARGET]))
""".replace("TARGET", repr(str(tmp_path)))
    process = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env=os.environ | {"PYTHONIOENCODING": "cp1252"},
        capture_output=True,
        timeout=15,
    )
    assert process.returncode == 0, process.stderr
    assert (tmp_path / "example.com/pages/index.md").read_text(encoding="utf-8") == "中文 €49"


def test_failed_competitor_summary_is_exported_and_sets_exit_code(tmp_path, monkeypatch):
    from scraper import cli

    class Failed(FixtureService):
        async def crawl_many(self, *args, **kwargs):
            async for result in super().crawl_many(*args, **kwargs):
                yield result.model_copy(update={"run_status": "partial"})

    monkeypatch.setattr(cli, "CompetitorScraper", Failed)
    assert cli.main(["https://one.example", "--output", str(tmp_path)]) == 1
    assert read_summary(tmp_path)["status"] == "partial"

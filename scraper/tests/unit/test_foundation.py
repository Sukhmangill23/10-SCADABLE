import json
import subprocess
import sys
from pathlib import Path

from scraper import CompetitorCrawlResult, CompetitorInput, ScrapedPage


def test_public_models_and_interfaces_import_without_loading_crawl4ai(tmp_path):
    code = (
        "import sys; import scraper; import scraper.interfaces; "
        "import scraper.crawl4ai_adapter; "
        "assert 'crawl4ai' not in sys.modules; print('browser-free import')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True, timeout=15
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "browser-free import"


def test_contracts_expose_json_schemas_for_integrators():
    for model in (CompetitorInput, ScrapedPage, CompetitorCrawlResult):
        schema = json.loads(json.dumps(model.model_json_schema()))
        assert schema["additionalProperties"] is False
        assert "homepage_url" in schema["properties"]


def test_synthetic_fixture_matches_installed_sdk_markdown_and_links_contract():
    from crawl4ai import CrawlResult

    path = Path(__file__).parents[1] / "fixtures" / "crawl4ai_success.json"
    result = CrawlResult.model_validate_json(path.read_text(encoding="utf-8"))
    assert result.markdown.raw_markdown.startswith("# Pricing")
    assert "$49/month" in result.markdown.fit_markdown
    assert result.links["internal"][0]["href"] == "https://example.com/features"
    assert result.links["external"][0]["href"] == "https://jobs.example.net/example"

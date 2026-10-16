# SCADABLE competitor scraper

Standalone Python package for discovering and collecting source-linked competitor content.
It is independent of the backend, database, LLM and frontend.

**Current status: Stage 1 foundation.** Models, configuration, component interfaces and SDK
configuration factories are implemented and tested. Discovery, browser execution, content
cleaning, file writers and the command-line scraper are delivered in Stages 2-4. There is
no crawl command or concrete scraper service yet.

## Setup and checks

Use Python 3.12 and [uv](https://docs.astral.sh/uv/). From the repository root:

```powershell
cd scraper
uv sync --locked
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
uv build
```

For pip users, runtime installation is also supported:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e .
```

The pip path installs runtime dependencies; uv is the supported way to reproduce the
locked development environment. No environment variables, service credentials or API
keys are needed. Python 3.12 is the supported baseline for this first release.

Browser binaries are not needed for Stage 1. Before browser execution is introduced,
install Chromium in the same environment using `uv run python -m playwright install chromium`.
On Linux, Playwright may also require OS libraries. See the official
[Crawl4AI installation guide](https://docs.crawl4ai.com/core/installation/).

Crawl4AI is pinned to 0.9.5. Pydantic provides validated, JSON-compatible contracts;
`tomllib` and the future CLI's `argparse` come from Python. Crawl4AI itself brings
LLM-related transitive dependencies; this package does not configure or call an LLM.

## Review the configuration

```python
from scadable_scraper import ScraperConfig, load_config, resolve_config

project = load_config("config.example.toml")
cli_overrides = ScraperConfig(max_pages=5)

for competitor in project.competitors:
    settings = resolve_config(
        project.global_settings,
        competitor.overrides,
        cli_overrides,
    )
    print(competitor.display_name, competitor.homepage_url, settings.max_pages)
```

Precedence is defaults < global settings < competitor overrides < explicit CLI overrides.
Only explicitly supplied fields override lower layers. Nested maps merge; lists replace,
including empty lists. Use `resolve_config()` rather than Pydantic's unvalidated
`model_copy(update=...)`. Competitor override serialization remains sparse, so saving and
reloading input JSON does not turn omitted settings into explicit overrides.

Unknown options, invalid limits, credentials embedded in URLs and subpage inputs are
rejected. Inputs must include `http://` or `https://`. An omitted competitor name falls
back to the homepage hostname with `www.` removed.

See [config.example.toml](config.example.toml) for two competitor inputs and a dynamic-page
rule. Its example domains are not live test targets. Settings express policies for the
later crawl service; configuration alone does not enforce domain or concurrency limits.

## Data contracts

```python
from datetime import UTC, datetime
from scadable_scraper import ScrapedPage

page = ScrapedPage(
    competitor_name="Example",
    homepage_url="https://example.com/",
    source_url="https://example.com/pricing",
    final_url="https://example.com/pricing",
    page_title="Pricing",
    page_category="pricing",
    crawl_timestamp=datetime.now(UTC),
    crawl_status="success",
    http_status=200,
    raw_markdown="# Pricing\n\nPro: $49/month",
    filtered_markdown="# Pricing\n\nPro: $49/month",
    cleaned_markdown="# Pricing\n\nPro: $49/month",
)
print(page.model_dump_json(indent=2))
restored = ScrapedPage.model_validate_json(page.model_dump_json())
```

`raw_markdown` preserves the full Markdown generated from the rendered source HTML.
`filtered_markdown` is the SDK's optional filtered version; `cleaned_markdown` is the
application's conservative normalized version. These fields are not interchangeable.
All timestamps require a timezone and serialize in UTC. Metadata must contain JSON values.
`source_url` is the requested source; `final_url` records redirects.

`CompetitorCrawlResult` includes schema version `1.0`, effective settings, page outcomes,
observed URL dispositions, derived counts, timing, warnings and the completion reason.
Failed pages require an error message and may preserve partial content. Skipped URLs are
registry entries, not pretend fetch results. Discovered/skipped/deferred/external URL
records preserve reasons and provenance. A discovery cap is reported explicitly.

Models support `model_dump(mode="json")`, `model_dump_json()` and `model_json_schema()`.
JSON/JSONL file writing is Stage 3 work; JSONL will contain typed `page` records followed
by a `competitor_summary` record without repeated page bodies.

## Boundaries and tests

- [models.py](src/scadable_scraper/models.py): application-owned fetch and result models.
- [config.py](src/scadable_scraper/config.py): validated settings, inputs and TOML resolution.
- [interfaces.py](src/scadable_scraper/interfaces.py): async service, fetching, sitemap,
  extraction and output contracts; no concrete implementations.
- [crawl4ai_adapter.py](src/scadable_scraper/crawl4ai_adapter.py): verified SDK configuration
  factories, with lazy SDK imports and no browser creation.
- [architecture.md](docs/architecture.md): approved policies, flow and stage boundaries.
- [tests](tests): offline model/configuration tests and real SDK configuration checks.

The public package and interface imports do not import Crawl4AI. Tests do not start
browsers, call an LLM or contact competitor websites. SDK-boundary tests instantiate real
SDK configuration objects rather than mocking their signatures. Synthetic fixtures in
`tests/fixtures` are available for later discovery/extraction tests.

Generated output, environments, caches, build artifacts and secrets are ignored by Git.
Each stage is reviewed and explicitly approved before its commit; no remote push is automatic.

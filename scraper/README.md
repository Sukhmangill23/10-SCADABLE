# SCADABLE competitor scraper

Standalone Python package for discovering and collecting source-linked competitor content.
It is independent of the backend, database, LLM and frontend.

**Current status: all four stages implemented and approved.** Sitemap/link discovery,
BestFirst/BFS traversal, Crawl4AI rendering, conservative extraction, JSON/JSONL output
and the multiple-homepage CLI are available, with bounded retries, resource cleanup,
interruption-safe file output and offline/browser verification. See the
[integration guide](docs/integration.md) for reliability and downstream consumption.
The approved three-page SCADABLE crawl and packaging checks are recorded in the
[validation report](docs/validation.md).
Start with the [quickstart guide](docs/quickstart.md) for setup, manual website tests
and inspecting the output.

## Setup and checks

Use Python 3.12 and [uv](https://docs.astral.sh/uv/). From the repository root:

```powershell
cd scraper
uv sync --locked
uv run --locked python -m playwright install chromium
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

The default tests do not require browser binaries. Real crawling requires Chromium.
On Linux, Playwright may also require OS libraries. See the official
[Crawl4AI installation guide](https://docs.crawl4ai.com/core/installation/).

Crawl4AI is pinned to 0.9.5. Pydantic provides validated, JSON-compatible contracts;
`tomllib` and the CLI's `argparse` come from Python. Crawl4AI itself brings
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
rule. Its example domains are not live test targets. Global concurrency settings are
shared ceilings for `crawl_many()`; individual competitors cannot raise those ceilings.

## Run the scraper

Replace the placeholders with competitor homepages you are authorized to crawl:

```powershell
uv run --locked scadable-scraper https://competitor-a.example https://competitor-b.example --output output/crawl.json
uv run --locked scadable-scraper --config config.toml --format jsonl --output output/crawl.jsonl
uv run --locked python -m scadable_scraper --help
```

Positional homepages select matching competitors from TOML, preserving their names and
overrides; unmatched homepages use global defaults. With no positional URLs, all TOML
competitors run. `--max-pages`, `--max-depth`, `--strategy` and `--max-concurrency` override
configuration. Existing output requires `--overwrite`; `--output -` emits structured
output to stdout. Diagnostics go to stderr. Exit codes: 0 successful page collection,
1 at least one partial/failed competitor, 2 input/output error, 130 interruption. Check
`completion_reason` and deferred URLs to assess coverage even when the exit code is 0.

For an importing application, use the asynchronous service directly:

```python
from scadable_scraper import CompetitorInput, ScraperConfig
from scadable_scraper.service import CompetitorScraper


async def collect(homepages: list[str]):
    scraper = CompetitorScraper()
    inputs = [CompetitorInput(homepage_url=url) for url in homepages]
    return [result async for result in scraper.crawl_many(inputs, ScraperConfig())]
```

No nested event loop, database, API server or LLM is required. See
[extraction guide](docs/extraction-and-output.md) for dynamic rules and streaming integration.

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
JSON uses `CrawlRunDocument` with `schema_version`, `serialized_at` and `results`.
JSONL contains typed `page` records followed by a `competitor_summary` record per
competitor, without repeated page bodies. Records are emitted as competitors complete.

## Boundaries and tests

- [models.py](src/models.py): application-owned fetch, result and output-record models.
- [config.py](src/config.py): validated settings, inputs and TOML resolution.
- [interfaces.py](src/interfaces.py): async component contracts.
- [crawl4ai_adapter.py](src/crawl4ai_adapter.py): verified SDK configuration
  factories, with lazy SDK imports and no browser creation.
- [browser.py](src/browser.py): rendering, guarded document requests and dynamic rules.
- [extraction.py](src/extraction.py): cleaning and keyword categories without network I/O.
- [service.py](src/service.py): reusable async service and shared page concurrency.
- [reliability.py](src/reliability.py): transient failure policy and bounded retry delays.
- [output.py](src/output.py) and [cli.py](src/cli.py): serialization and standalone execution.
- [architecture.md](docs/architecture.md): approved policies, flow and stage boundaries.
- [integration.md](docs/integration.md): deadlines, interruption behavior and consumer examples.
- [tests](tests): fixture-based workflow checks and opt-in loopback browser tests.

The public package and interface imports do not import Crawl4AI. Default tests use
synthetic fixtures and mocked HTTP/rendering boundaries. Opt-in tests launch Chromium
against loopback fixture servers only; no competitor website or LLM is contacted:

```powershell
$env:SCADABLE_BROWSER_TESTS = "1"
uv run --locked pytest tests/integration/test_browser_local.py -q
```

Generated output, environments, caches, build artifacts and secrets are ignored by Git.
Each stage is reviewed and explicitly approved before its commit; no remote push is automatic.

# Scraper and LLM research pipeline

The scraper owns discovery, Decisions scoring, rendering, Markdown cleanup, and export.
The separate LLM layer consumes those exports to extract cited facts and produce company
analysis. No API server, database, scheduler, or frontend integration is included.

```text
CompetitorInput URLs
  -> CompetitorScraper.crawl_many() + Decisions
  -> export_competitor(): crawl_summary.json + pages/*.md
  -> load_analysis_input(): validated metadata + exact Markdown
  -> Analyzer.extract_information() -> Analyzer.analyze_competitor()
  -> CompetitorResearchResult: crawl provenance + facts + analysis
```

## Setup

Use Python 3.12. From the repository root, install both local packages together:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install ./scraper -e ".[dev]"
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

On macOS/Linux, activate with `source .venv/bin/activate` and create `.env` from
`.env.example` if absent. The root project's uv source configuration also points to the
local `scraper/` package. The documented pip command supplies that local package explicitly.

The combined environment installs the scraper as a regular package to avoid an editable
import collision with the outer `scraper/` directory. Reinstall `./scraper` after changing
its source. Its independent, editable development setup remains in
[scraper/README.md](../scraper/README.md).

Both layers default to the same repository-root `.env`, even when launched from `scraper/`
or another nested directory. `scraper/.env` is no longer used. Set `OPENAI_API_KEY` and
`OPENAI_MODEL` in the root file or the process environment. The analysis
model must support Responses API structured outputs. Tests and example `--help` need no
real credentials. Offline tests also need no browser binaries.

For live crawling, install Chromium. These optional PowerShell cache settings reuse the
scraper's ignored local cache directories and should be set in each new terminal:

```powershell
$env:CRAWL4_AI_BASE_DIRECTORY = Join-Path (Get-Location) "scraper/.uv-cache"
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Get-Location) "scraper/.uv-cache/playwright"
python -m playwright install chromium
```

See the [scraper quickstart](../scraper/docs/quickstart.md) for browser and site-specific setup.

## Run the example

Analyze a published export without crawling again:

```powershell
python examples/research_pipeline.py --export scraper/output/run-001/example.com/crawl_summary.json
```

Or replace this example URL with a competitor homepage to collect and analyze fresh content:

```powershell
python examples/research_pipeline.py https://competitor.example/ --max-pages 3
```

Multiple homepage arguments are supported. By default, each invocation chooses a fresh
UTC-named directory under `scraper/output/`. Use `--output` to choose a fresh run root,
`--env-file` to select a credential file, or `--selection-mode structural` to disable only
the scraper's model requests. Downstream analysis still uses OpenAI.

The example prints a JSON array of research results. Page Markdown and `crawl_summary.json`
keep the scraper's existing output structure; analysis does not rewrite those files.

## Python interfaces

The top-level `scraper/` and `llm/` directories keep collection and analysis separate.
The root project packages `llm/` directly; analysis imports use `llm.*`, including
`llm.config` for settings and `llm.pipeline` for orchestration.

```text
scraper/           Standalone collection package and documentation
llm/
  config.py        Analysis environment settings
  pipeline.py      Scraper export and analysis orchestration
  inputs.py        Markdown bundle loader
  analyzer.py      Extraction, company analysis, and comparison
  client.py        OpenAI structured-output client
  schemas.py       Analysis input and output contracts
  swot_entries.py  Source-linked SWOT rows
  prompts/         Extraction, analysis, and comparison instructions
```

| Interface | Purpose and return value |
| --- | --- |
| `load_analysis_input(summary_path)` | Synchronously read a validated bundle into `AnalysisInput` |
| `await analyze_export(summary_path, analyzer=...)` | Analyze a saved bundle; optional `is_scadable=True` selects the existing SCADABLE method |
| `await run_pipeline(competitors, output_directory=..., analyzer=...)` | Collect and analyze a sequence of `CompetitorInput`; return research results in crawl-completion order |
| `await run_competitor(competitor, ...)` / `await run_scadable(scadable, ...)` | Return one `CompetitorResearchResult` using the appropriate company-analysis method |
| `await run_comparison(scadable, competitors=..., ...)` | Collect all companies through one shared crawl and pass competitor analyses in input order to the existing SWOT comparison |

The collection functions accept optional `scraper_settings: ScraperConfig` and an injected
`scraper: ScraperService`. `run_pipeline(..., scadable=...)` includes SCADABLE in the same
shared crawl and returns its company result alongside the competitors. Existing analysis
results can be compared directly with `Analyzer.compare(ComparisonInput(...))` without
another crawl.

The caller chooses credentials and owns the analysis client's lifetime:

```python
from llm.analyzer import Analyzer
from llm.client import OpenAIClient
from llm.config import Settings
from llm.pipeline import run_pipeline
from scraper import CompetitorInput, ScraperConfig
from scraper.environment import load_environment


async def research():
    load_environment()  # Shared repository-root .env; process values win.
    client = OpenAIClient(Settings(_env_file=None))
    try:
        return await run_pipeline(
            [
                CompetitorInput(
                    homepage_url="https://competitor.example/", name="Example"
                )
            ],
            output_directory="scraper/output/run-001",  # Choose a fresh root.
            scraper_settings=ScraperConfig(max_pages=3),
            analyzer=Analyzer(client),
        )
    finally:
        await client.close()
```

Await `research()` in an existing event loop. A standalone script can use
`asyncio.run(research())`. The pipeline moves export/read operations to worker threads;
it does not start a nested event loop or close an injected analysis client.

## Configuration and results

| Configuration | Owner |
| --- | --- |
| `ScraperConfig` / `SelectionConfig`, including TOML overrides | Collection policy, limits, Decisions model, and estimated Decisions budget |
| `OPENAI_API_KEY` | Shared credential for Decisions and downstream analysis |
| `OPENAI_MODEL` | Downstream analysis model; does not change the Decisions model |
| `OPENAI_TIMEOUT_SECONDS` | Analysis SDK request timeout; default 30 seconds |

`Settings()` and `load_environment()` use the same repository-root `.env` by default.
The resolver identifies the checkout from its `pyproject.toml`, `scraper/pyproject.toml`,
and `llm/` directory, checking the working directory's ancestors and the scraper module's
ancestors. Without a checkout, installed packages default to the working directory's `.env`.
Calling `load_environment(path)`
explicitly and then `Settings(_env_file=None)` lets an importing application choose one
credential source. Process environment variables take precedence. The old provider-selector
settings have been removed; collection always uses the standalone scraper.

Each `CompetitorResearchResult` contains:

- `crawl_summary`: the unchanged schema `2.1` scraper index, including source/final URLs,
  page file references, titles, categories, UTC timestamps, counts, warnings, and Decisions usage.
- `extracted_information`: the existing `ExtractedInformation` with categorized, cited facts.
- `analysis`: the existing `CompanyAnalysis` with cited strengths/weaknesses and feature scores.

Serialize with `result.model_dump(mode="json")` or `result.model_dump_json()`. The
[scraper output guide](../scraper/docs/output-layout.md) remains the authority for filenames,
completion markers, provenance, and no-overwrite behavior.

## Failure handling and current limits

- The loader requires a valid completion index and follows its `markdown_file` references.
  It analyzes successful, nonempty pages; failed and blank-page records remain in the summary.
  Partial runs with usable content retain their status and warnings.
- No usable pages, invalid indexes, missing files, or invalid UTF-8 fail before an analysis
  request. Existing competitor output folders and conflicting competitor folder names are rejected
  before crawling.
- Extraction citations must match original source URLs. Company-analysis citations must
  occur in the extracted facts. Redirect destinations remain metadata, not replacement citations.
- A batch fails fast when a company has no usable content or export/analysis raises.
  The crawl iterator is closed when supported, including on cancellation. Published exports
  remain available for `analyze_export()` retries; cancellation does not roll back files.
- Full Markdown is supplied without chunking or truncation. Model context-limit errors
  propagate. The Decisions allowance applies only to selection, not downstream analysis costs.

## Verification

From the repository root, using the combined environment:

```powershell
python -m pytest tests -q
python -m pytest -c scraper/pyproject.toml scraper/tests -q
python -m pytest tests/test_research_integration.py -q
python examples/research_pipeline.py --help
```

The integration test uses the real service, Decisions adapter, exporter, loader, analyzer,
and SDK parsing with browser/HTTP boundaries mocked. It verifies exact Markdown, metadata,
citations, client cleanup, and replay without recrawling. Other tests cover invalid bundles,
configuration, comparison ordering, cancellation, schemas, and score bounds.
Opt-in Chromium tests and standalone checks remain in the scraper's own documentation.

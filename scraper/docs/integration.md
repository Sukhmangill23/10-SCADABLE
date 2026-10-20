# Reliability and integration

This guide covers the independently usable scraper package. For the repository's
working Markdown-to-LLM workflow, see the [research pipeline guide](../../docs/research-pipeline.md).

The package runs without a backend, database or downstream analysis service. Install using
`uv sync --locked`, then `uv run --locked python -m playwright install chromium`.
Run the CLI from any directory after installation; use an explicit TOML/output path.
For a custom browser location, set `PLAYWRIGHT_BROWSERS_PATH` during both installation
and execution. The browser boundary automatically reuses `scraper/.uv-cache/playwright`
when present in this checkout, using the same setup as the manual runner. Explicit
host configuration wins; installed packages outside a checkout retain SDK defaults.
The CLI and manual runner default to the shared repository-root `.env`;
the CLI supports an explicit `--env-file`. Existing process environment
values take precedence. Default LLM selection requires `OPENAI_API_KEY`; explicit
`selection={"mode": "structural"}` needs no API credentials or model requests.

Crawl4AI initializes an import-time SDK cache under the user home even when application
page caching is disabled. Checkout browser startup defaults this to `scraper/.uv-cache`.
In a restricted deployment, set `CRAWL4_AI_BASE_DIRECTORY`
to a writable directory before Python starts (the SDK creates `.crawl4ai` beneath it).
For example, from `scraper/` in PowerShell:

```powershell
$env:CRAWL4_AI_BASE_DIRECTORY = Join-Path (Get-Location) ".uv-cache"
```

This is an SDK runtime cache, not application persistence. Keep it out of Git.
`CRAWL4AI_NO_CLOUD_NOTICE=1` optionally suppresses the SDK's stderr promotional notice.
Install Chromium during deployment setup with the same interpreter and browser-cache
setting used by the worker. Linux images need system dependencies too, for example
`python -m playwright install --with-deps chromium`. Requests never install browsers.
Await cancellation: browser startup and cleanup finish within their configured deadlines
before the cancellation propagates, preventing abandoned driver transports.

## Python consumers

Use the existing event loop in an importing application:

```python
from contextlib import aclosing
from scraper import CompetitorInput, ScraperConfig, SelectionConfig
from scraper.environment import load_environment
from scraper.service import CompetitorScraper


async def collect(homepages, consume):
    load_environment()  # Shared repository-root .env, or supply your application's path.
    service = CompetitorScraper()
    inputs = [CompetitorInput(homepage_url=url) for url in homepages]
    settings = ScraperConfig(selection=SelectionConfig(budget_usd=0.03))
    async with aclosing(service.crawl_many(inputs, settings)) as results:
        async for result in results:
            await consume(result.model_dump(mode="json"))
```

For one competitor, `await service.crawl(competitor, settings)` returns a validated
`CompetitorCrawlResult`. A result is yielded only after that competitor completes.
`aclosing` ensures early loop exit or consumer failure cancels the remaining workers
and closes their resources. Cancellation propagates; it does not fabricate a complete
result for the interrupted competitor. The service does not create a nested event loop.
Library imports and service constructors do not read `.env` implicitly: the importing
application chooses when and where to load it. `load_environment(path, required=True)`
rejects a missing explicit file; by default an absent file is optional, supporting
structural mode or credentials supplied by the host environment. Missing required LLM
credentials still fail before browser/network activity. Credential values are not logged
or added to serialized scraper settings.

The FastAPI team can await this interface or consume its exported files. Request lifetime,
background execution and persistence belong to that application. No endpoints or database
code are included here. Each result retains effective configuration for reproducibility.

The analysis team should select pages with `crawl_status == "success"` and use
`cleaned_markdown` with `source_url`, `final_url`, title, category and UTC timestamp.
`raw_markdown` retains the full SDK source Markdown; optional `filtered_markdown` may
omit useful details. Failed pages may retain partial source content and an error message;
decide explicitly whether to analyze them. Categories consume content-based Decisions
assessments and use `other` when unavailable. Research selection is separate from downstream
company analysis; see [decisions.md](decisions.md).

## Exporting and reading results

The repository's `pipeline.analyze_export()` validates this same completion index and
reads its successful, nonempty Markdown files without recrawling or cleaning them again.
It returns extracted facts, company analysis and the original summary. The separate
analysis client requires `OPENAI_MODEL`; the Decisions allowance does not cover its
requests. Setup, client ownership and replay examples are in the research pipeline guide.

The service API still returns full `CompetitorCrawlResult` objects. To write the compact
file export, call the synchronous exporter after a competitor completes:

```python
from scraper.output import export_competitor

# result = await service.crawl(competitor, settings)
# summary = export_competitor(result, "output/run-001")
```

Each website has a `crawl_summary.json` and relative content-only Markdown files.
The file index uses schema `2.1`; full in-memory results use schema `1.1` and include
typed assessments, selection diagnostics, usage, and optional in-memory decision traces.
Read and validate the index, then follow its Markdown references:

```python
from pathlib import Path
from scraper import CrawlExportSummary

index = Path("output/run-001/competitor.example/crawl_summary.json")
summary = CrawlExportSummary.model_validate_json(index.read_text(encoding="utf-8"))
for page in summary.pages:
    if page.status == "success":
        content = (index.parent / page.markdown_file).read_text(encoding="utf-8")
        # Supply content, page.url, page.title, page.category and page.crawled_at
        # to the application's next processing step.

if summary.decision_usage:
    usage = summary.decision_usage
    print(usage.effective_mode, usage.estimated_cost_usd, usage.fallback_events)
```

`page.selection` exposes method, available relevance score and assessment availability.
It describes why the application fetched that page; it is not verified company analysis.
The Python page's `content_assessment` retains independent usefulness/novelty/category
results and question-level issues. Successful pages remain available regardless of score.

For opt-in traces, set `selection.trace_enabled=True` before crawling, then read the
fixed relative `summary.decision_trace_file` if present. Each UTF-8 JSONL line validates
as `scraper.decision_models.DecisionTraceRecord`. It contains bounded request evidence,
typed rubric answers, timings, token accounting and sanitized error codes; keys and
authorization headers are absent. This trace is published before the summary marker.
An enabled trace may be empty. Disabled tracing never exports the result's trace list.

`decision_usage` distinguishes reported input tokens from uncertain reservations for
dispatched requests without usage. Estimated cost is not a guaranteed billing ceiling.
Budget/transient API fallback records a warning and effective structural mode without
making otherwise successful collection fail. Authentication/access errors stop the
affected competitor and retain already-collected pages. Missing credentials fail before
browser/network activity. See [migration.md](migration.md) for strict-reader changes.

`CrawlExportSummary` validates counts, unique references and safe relative Markdown paths.
Its JSON contains no content bodies, raw SDK metadata or full effective configuration.
The full Python result retains that information. `pages` lists attempted outcomes;
`uncrawled_urls` explains skipped, deferred, external or pending discoveries. Each entry
contains its recorded depth/source/parent relationships. Missing optional values are
omitted. Detailed naming and timing semantics are in [output-layout.md](output-layout.md).

The legacy JSON/JSONL file writers, record models and parsing helpers were removed.
Existing generated files are left in place. Exporting already-held Python results does
not fetch the website again. Choose a new output root to retain successive runs.

## Retry and deadline policy

| Failure | Behavior |
| --- | --- |
| Network connection failures/timeouts; HTTP 408/429/500/502/503/504 | At most `max_retries` retries, default 2 |
| Other HTTP statuses; domain/robots refusal; empty content; configuration/internal errors | Preserve failure, no page retry |
| Capacity/rate wait deadline | Preserve capacity failure, no retry |
| Extraction error | Preserve that page's source and error; continue other pages |
| Cancellation | Propagate and release resources |

The service owns page retries, including failures returned by Crawl4AI. Recognized SDK
navigation/readiness timeout envelopes and transient network codes are classified
conservatively because the SDK wraps typed exceptions in result messages. Unknown
SDK failures are retained without retry. Typed interaction errors are captured at the hook.
SDK and Playwright route retries are disabled to avoid multiplying attempts.

Retry delays use exponential ceilings of 1, 2, 4, ... seconds, capped by
`max_backoff_seconds` (30), with jitter between half and all of that ceiling.
Valid `Retry-After` seconds/HTTP dates extend the wait. A wait above the configured
backoff bound stops requests to that hostname for the run instead of retrying early.
Cooldowns are shared across browser, robots and sitemap requests. Already in-flight
requests cannot be recalled. Invalid headers fall back to normal backoff.

Each distinct page, including a failed page, consumes one page reservation. Its retries
reuse that reservation. `attempt_count` counts logical browser/fetch attempts; it does
not count robots, redirects, rendering resources or sitemap HTTP requests. Final page
metadata contains `crawl_diagnostics.attempts` (status, error, kind, duration and retry
delay) and `stop_reason`. Raw/filtered content describes the final attempt.

The bounded HTTP reader independently retries transient discovery requests. Every
attempt and redirect consumes its existing `max_sitemap_requests` budget. Total sitemap
discovery remains bounded by `discovery_timeout_seconds`; exhaustion produces warnings
and partial discovery rather than unrestricted requests. Robots failures remain cached
and fail closed; missing robots (404/410) is distinct from access/server failure.

Defaults and ownership:

- `page_timeout_seconds=45`: cumulative active SDK work across a page attempt's redirects.
  Retries get fresh attempt budgets. Browser startup has the same configured deadline.
- `capacity_wait_timeout_seconds=120`: each capacity acquisition or document pacing wait,
  excluded from active rendering time. The outer deadline controls active work while the
  SDK navigation timer allows the separately bounded routing wait.
- `discovery_timeout_seconds=30`: discovery/robots deadlines; HTTPX also has request timeouts.
- Browser cleanup is bounded at 10 seconds and each owned page close at 5 seconds.
  Cleanup errors are logged without replacing collected results.

Backoff releases page/hostname slots. Global/CLI concurrency settings are shared ceilings
for a `crawl_many` run. Competitor settings can lower local concurrency. Rate limits apply
to document/discovery starts, not every image/script/XHR required to render a page.
These bounds compose; `page_timeout_seconds` is not a whole-run wall-clock deadline.

Document requests and every redirect must pass exact-host and robots checks. Additional
domains require explicit configuration approval. Third-party rendering resources are
allowed under the approved policy; popups/embedded documents are blocked. TLS verification
is enabled. There is no anti-bot bypass or authentication workflow.

## Output and operational behavior

`--output` is a directory, defaulting to `output/`. Each completed competitor writes one
Markdown bundle and its index; the CLI logs the saved index path to stderr. Existing
competitor directories are rejected before starting the CLI crawl and checked again
when exporting. Use a fresh root such as `--output output/run-002` for repeat runs.
`--format`, `--overwrite` and `--output -` are no longer supported.

All page content and JSON are UTF-8. Files are written to an owned temporary directory
under the output root before publication. The exporter reserves the final directory
with an exclusive mkdir, moves its pages and optional trace, and publishes the index last.
A staging error removes its temporary files. A publication error or forced termination may leave an
incomplete folder without an index, or a hidden staging directory after a hard kill.
Require `crawl_summary.json` before accepting the export and use a fresh output root
instead of replacing an incomplete folder. This is summary-last publication, not a
filesystem-wide transaction or a power-loss durability guarantee.

Completed competitor bundles survive later cancellation or output errors. The CLI closes
the async iterator on consumer/output failure, cancelling remaining workers. No existing
crawl files or unrelated user data are automatically deleted, migrated or overwritten.
There is no automatic resume or append mode.

Normal INFO logs report competitor start/end, attempts and output locations; `--verbose`
enables DEBUG. Exit codes remain 0 for successful collection, 1 for a partial/failed
competitor, 2 for input/output errors and 130 for interruption. Check `completion_reason`,
optional warnings/truncation flags and uncrawled URL reasons even with exit 0. Page/depth
limits do not imply exhaustive coverage.

## Verification and test boundaries

From `scraper/`:

```powershell
uv sync --locked
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
uv build
uv run --locked scraper --help
$env:SCRAPER_BROWSER_TESTS = "1"
uv run --locked pytest tests/integration/test_browser_local.py -q
```

Default tests mock HTTP/browser boundaries and exercise real models/frontier/service.
Opt-in Chromium tests use loopback fixtures for redirects, dynamic content, HTTP retry
recovery, permanent errors and SDK-wrapped selector timeouts. No live domain is contacted
by the suite. Live validation is separate and requires explicit target approval.

For custom test fetchers, implement the async `PageFetcher` contract and inject
`fetcher_factory`; inject `http_transport` for robots/sitemap fixtures. Fetchers should
make one attempt and let the service own retries. Raise `TimeoutError`/`ConnectionError`
for typed transient failures, or return a `FetchedPage` with HTTP status/response headers.
Returned non-HTTP failures may specify `metadata.crawl_diagnostics.failure_kind` as
`network`, `timeout`, `policy` or `internal`. Unknown failures are not assumed transient.

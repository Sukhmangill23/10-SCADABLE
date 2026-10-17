# Reliability and integration

The package runs without a backend, database or LLM. Install with Python 3.12 using
`uv sync --locked`, then `uv run --locked python -m playwright install chromium`.
Run the CLI from any directory after installation; use an explicit TOML/output path.
For a custom browser location, set `PLAYWRIGHT_BROWSERS_PATH` during both installation
and execution. No service credentials are required.

Crawl4AI initializes an import-time SDK cache under the user home even when application
page caching is disabled. In a restricted deployment, set `CRAWL4_AI_BASE_DIRECTORY`
to a writable directory before Python starts (the SDK creates `.crawl4ai` beneath it).
For example, from `scraper/` in PowerShell:

```powershell
$env:CRAWL4_AI_BASE_DIRECTORY = Join-Path (Get-Location) ".uv-cache"
```

This is an SDK runtime cache, not application persistence. Keep it out of Git.
`CRAWL4AI_NO_CLOUD_NOTICE=1` optionally suppresses the SDK's stderr promotional notice.

## Python consumers

Use the existing event loop in an importing application:

```python
from contextlib import aclosing
from scadable_scraper import CompetitorInput, ScraperConfig
from scadable_scraper.service import CompetitorScraper


async def collect(homepages, consume):
    service = CompetitorScraper()
    inputs = [CompetitorInput(homepage_url=url) for url in homepages]
    async with aclosing(service.crawl_many(inputs, ScraperConfig())) as results:
        async for result in results:
            await consume(result.model_dump(mode="json"))
```

For one competitor, `await service.crawl(competitor, settings)` returns a validated
`CompetitorCrawlResult`. A result is yielded only after that competitor completes.
`aclosing` ensures early loop exit or consumer failure cancels the remaining workers
and closes their resources. Cancellation propagates; it does not fabricate a complete
result for the interrupted competitor. The service does not create a nested event loop.

The FastAPI team can await this interface or consume its exported files. Request lifetime,
background execution and persistence belong to that application. No endpoints or database
code are included here. Each result retains effective configuration for reproducibility.

The analysis team should select pages with `crawl_status == "success"` and use
`cleaned_markdown` with `source_url`, `final_url`, title, category and UTC timestamp.
`raw_markdown` retains the full SDK source Markdown; optional `filtered_markdown` may
omit useful details. Failed pages may retain partial source content and an error message;
decide explicitly whether to analyze them. Categories are keyword labels, not LLM judgments.

## Reading exported files

JSON is a complete versioned document:

```python
from pathlib import Path
from scadable_scraper import CrawlRunDocument

document = CrawlRunDocument.model_validate_json(
    Path("output/crawl.json").read_text(encoding="utf-8")
)
for result in document.results:
    print(result.homepage_url, result.summary.successful, result.completion_reason)
```

JSONL groups page records followed by the completed competitor's summary. Reconstruct
and validate its counts before accepting it:

```python
from pathlib import Path
from scadable_scraper import CompetitorCrawlResult
from scadable_scraper.output import parse_jsonl_record

pending = {}
completed = []
with Path("output/crawl.jsonl").open(encoding="utf-8") as stream:
    for line in stream:
        record = parse_jsonl_record(line)
        if record.record_type == "page":
            key = str(record.page.homepage_url)
            pending.setdefault(key, []).append(record.page)
        else:
            key = str(record.result.homepage_url)
            completed.append(
                CompetitorCrawlResult.model_validate(
                    {**record.result.model_dump(), "pages": pending.pop(key, [])}
                )
            )
# Any remaining pending pages lack a completion summary and are not complete results.
```

An interrupted write can leave a malformed final JSONL line. A recovery consumer may
discard that final partial record and pending pages; malformed earlier records should
be reported rather than ignored. CLI inputs deduplicate competitor homepages within a run.
Keep separate run files when collecting the same homepage repeatedly. All models expose
`model_json_schema()`; output schema remains `1.0`.

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

JSON file output uses a same-directory temporary file, flush/fsync and atomic publication.
With `--overwrite`, the old file remains until replacement; without it, concurrent creation
of the target is detected atomically. This requires ordinary local filesystem hard-link
support. The CLI reports an output error on unsupported filesystems. On handled errors or
interruption the temporary file is removed; a forced process kill may leave a `.tmp` file.
Atomic visibility does not promise power-loss durability of the directory entry.

JSONL writes completed competitors and flushes each summary. An interruption retains
earlier complete competitors. With `--overwrite`, JSONL truncates the old output on start;
choose a fresh path when the old file must be retained. Stdout is UTF-8 and cannot provide
atomic-file guarantees. Output/consumer errors close the async iterator immediately.
There is no automatic resume or append mode.

Normal INFO logs report competitor start/end and page attempts; `--verbose` enables DEBUG.
SDK/CLI diagnostics use stderr; stdout remains structured data with `--output -`.
Exit codes: 0 successful collection, 1 partial/failed competitor, 2 input/output error,
130 interruption. Check `completion_reason`, warnings, `discovery_truncated` and deferred
URL reasons even with exit 0. Reaching a page/depth limit does not imply exhaustive coverage.

## Verification and test boundaries

From `scraper/`:

```powershell
uv sync --locked
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
uv build
uv run --locked scadable-scraper --help
$env:SCADABLE_BROWSER_TESTS = "1"
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

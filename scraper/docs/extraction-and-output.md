# Stage 3: rendering, extraction and output

## Data flow and component API

`CompetitorScraper.crawl()` returns one `CompetitorCrawlResult`. `crawl_many()` is an
async iterator yielding complete competitor results in completion order. Each run uses
the existing discovery frontier and keeps its fetched pages for extraction without
another request. A browser belongs to one competitor; HTTP clients, browsers and owned
pages close on normal exit or cancellation. Service objects do not own an event loop.

```python
from contextlib import aclosing
from scadable_scraper import CompetitorInput, ScraperConfig
from scadable_scraper.service import CompetitorScraper


async def collect_or_stop(homepages, consume):
    service = CompetitorScraper()
    competitors = [CompetitorInput(homepage_url=url) for url in homepages]
    async with aclosing(service.crawl_many(competitors, ScraperConfig())) as results:
        async for result in results:
            if not await consume(result):
                break  # aclosing cancels remaining workers and releases their browsers
```

Models, interfaces and the service can be imported without loading the SDK. The browser
starts on entering the fetcher's async context. An injected `fetcher_factory(competitor,
settings, robots_guard)` supports backend tests without browsers. An optional HTTPX
transport replaces sitemap/robots HTTP at its network boundary for offline fixtures.

`crawl_many()` shares global/CLI page and hostname concurrency ceilings across competitors.
Effective per-competitor settings still describe that competitor's discovery limits;
shared ceilings apply in addition. Page starts on a shared hostname respect configured
spacing and robots minimum intervals. The default browser adapter reserves a hostname
slot for every actual render hop, including redirect destinations, and shares document
start pacing across competitors. Custom fetcher factories receive source-host limits
from the service and own their internal redirect policy; a custom Crawl4AI adapter can
receive a shared `HostLimiter` explicitly. The service also shares that limiter with
robots and sitemap HTTP; the HTTP request budget remains separate from page reservations.
Rendering resources are not counted as independently crawled pages.

## Browser and dynamic-page policy

Crawl4AI 0.9.5 supplies Chromium rendering, HTML/metadata/link extraction and Markdown
generation. The public page-context hook installs document routing before navigation.
The existing exact-host/Protego guard is the robots authority; the adapter disables
the redundant SDK robots lookup and uses the same explicit user agent everywhere.

Each main document request uses Playwright `route.fetch(max_redirects=0, max_retries=0)`.
For a redirect, the adapter aborts the current browser navigation and starts the next
SDK navigation only after checking the destination. It never sends the redirect response
to the browser, which would otherwise let automatic redirect hops bypass routing.
The final page is rendered at its real URL, retaining normal relative-link resolution.
All redirect hops share one attempt deadline and distinct-page reservation. Redirect
history is retained in metadata. An SDK navigation abort is expected during this process.

Third-party scripts, styles, images and fetch/XHR requests are allowed for rendering.
Embedded documents, popups, non-GET documents and unexpected document navigation are
blocked; iframe content is not collected. Service-worker bypass is enabled per page.
An ordinary link is discovered rather than clicked. JavaScript-only controls that replace
the entire document are not supported as load-more buttons; use page links/configuration
appropriate to that site. Public HTML pages are supported; PDF extraction is outside scope.

The first matching `dynamic_rules` URL glob wins. Its explicitly configured fields override
`global.dynamic`, retaining omitted global fields. Rules are reevaluated after redirects.
CSS waits, SDK scrolling and configured button clicks have finite limits. A missing,
hidden or disabled load-more button ends pagination normally; interaction errors fail
that page. `scroll_delay_seconds` also supplies the pause after each click; sites loading
asynchronously may need a longer pause. Content already present in the DOM is extracted;
there is no claim that arbitrary infinite scrolling or virtualized lists are exhausted.

```toml
[[competitors.overrides.dynamic_rules]]
url_pattern = "https://competitor.example/careers*"
wait_for_css = "main.jobs"
scan_full_page = true
max_scroll_steps = 5
load_more_selector = "button.load-more"
max_clicks = 3
scroll_delay_seconds = 0.5
```

Pagination URLs found in links enter the shared frontier and obey its normal page/depth
budgets. Same-document load-more interactions count toward the current page's finite
click/time limits. Source content and links come from the final rendered DOM snapshot.

## Content and categorization

- `raw_markdown`: unchanged SDK Markdown generated from rendered `raw_html`, retaining
  links. It is full readable Markdown, not byte-for-byte HTML or a script archive.
- `filtered_markdown`: SDK `PruningContentFilterLXML` output (threshold 0.2, minimum word
  threshold 0). This representation can omit useful material and is never substituted
  for the source or conservative cleaned version.
- `cleaned_markdown`: full Markdown with normalized line endings and unsafe control
  characters removed. Indentation, hard breaks, blank lines, tables and code are preserved.

`MarkdownExtractor` requires no network access. Categories use the same official keyword
scorer and configured URL/title weights as discovery. The strongest weighted category
wins; ties use `PageCategory` enum order (pricing precedes products/features/blog; careers
precedes hiring). The final URL is preferred when available. Unmatched homepage content
falls back to positioning; other unmatched pages use `other`. One category is a coarse
source label, not a claim that a mixed page contains only that kind of information.

SDK metadata and response headers are JSON-normalized and preserved. Adapter metadata
adds redirect history, load-more click count and up to 20 blocked embedded document URLs.
Failed SDK results can retain partial content. HTTP errors and empty Markdown are failures.
Extraction failures are reconciled with URL dispositions so result counts stay consistent.

## JSON and JSONL contracts

JSON root: `{"schema_version":"1.0", "serialized_at":"...", "results":[...]}`.
Every result includes pages, effective settings, discovered URL provenance/dispositions,
derived summary counts, warnings, timing, run status and completion reason.

JSONL records are independently Pydantic-validatable discriminated records:

```json
{"schema_version":"1.0","record_type":"page","page":{"...":"ScrapedPage fields"}}
{"schema_version":"1.0","record_type":"competitor_summary","result":{"...":"result fields except pages"}}
```

These are shape illustrations; see the models' `model_json_schema()` for complete schemas.
`parse_jsonl_record(line)` returns a `PageRecord` or `CompetitorSummaryRecord`. To restore
a complete result, group page records by homepage, then validate the summary payload
plus those pages using `CompetitorCrawlResult.model_validate()`. That step checks page
counts against the summary. A summary record alone cannot verify omitted page bodies.

`write_json(document, stream)` and `JsonlSink(stream)` use caller-owned text streams.
The CLI emits records when a competitor completes; it does not stream pages during that
competitor's discovery. A JSONL summary flushes its completed competitor. JSON is written
after all competitors finish. JSON file publication is atomic; an interruption preserves
the prior file (or leaves a new target absent). JSONL retains completed competitors;
consumers must require a summary before treating a competitor as complete. Files require
`--overwrite` to replace existing content. No generated output belongs in Git.

## Verification and current limits

```powershell
uv sync --locked
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
uv build
uv run --locked scadable-scraper --help
```

Opt-in Chromium verification uses only local fixture servers:

```powershell
uv run --locked python -m playwright install chromium
$env:SCADABLE_BROWSER_TESTS = "1"
uv run --locked pytest tests/integration/test_browser_local.py -q
```

If browser binaries are stored in a custom directory, set `PLAYWRIGHT_BROWSERS_PATH` for
both installation and execution. During development they were stored in the ignored
`.uv-cache/playwright` directory. The cross-host loopback-script fixture grants a local
network permission in its test-only subclass; production does not grant it.

The service implements bounded transient retries and records actual `attempt_count` plus
per-attempt diagnostics. Capacity and rate waits have a separate deadline from rendering.
See [integration.md](integration.md) for reliability, failure classifications and consumer
examples. Stage 3 was approved and committed as `f801e62`; Stage 4 is also approved.

Official references: [Markdown generation](https://docs.crawl4ai.com/core/markdown-generation/),
[browser hooks](https://docs.crawl4ai.com/advanced/hooks-auth/),
[page interactions](https://docs.crawl4ai.com/core/page-interaction/),
[Playwright route fetching](https://playwright.dev/python/docs/api/class-route#route-fetch).

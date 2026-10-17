# Stage 4 validation report

This report records the historical Stage 4 checks and live crawl. The current CLI now
exports Markdown bundles and schema `2.0` summary indexes; its output refactor verification
is recorded in [output-validation.md](output-validation.md). Existing historical JSON/JSONL
artifacts below are retained as source data, not current CLI examples.

Implementation base: Stage 3 commit `f801e62`. Stage 4 implementation and its commit
were explicitly approved by the user. No remote push was performed.

## Automated checks

- Full suite including opt-in loopback Chromium: **241 passed in 32.71 seconds**.
- Default offline suite: **234 passed, 7 opt-in browser cases skipped in 16.33 seconds**.
- Ruff lint and formatting, lock consistency, diff whitespace check and source/wheel
  builds passed locally.
- Independent read-only review found three reliability issues, now corrected: pacing
  consuming rendering time, concurrent requests bypassing Retry-After, and SDK-wrapped
  timeouts missing retries. Re-review found no remaining Critical or Important issues.
- Installed the `scraper-0.1.0-py3-none-any.whl` wheel with runtime dependencies into
  a fresh ignored `output/wheel-venv` using the offline package cache. An isolated Python
  process verified imports came from that wheel, then processed two mocked competitors
  through the library API and roundtripped both JSON and JSONL. Both installed CLI entry
  points (`scraper --help` and `python -m scraper --help`) succeeded.

After generalizing the package name to `scraper`, the full suite passed again:
**241 passed in 35.10 seconds**. A fresh wheel install under `output/rename-venv`
verified the renamed imports, both CLI entry points, two mocked competitors and
JSON/JSONL roundtrips. Wheel paths contain only the generic package name; the lockfile
retains all dependency versions. No additional live website requests were made.

The suite covers transient/permanent HTTP failures, request/page budgets, Retry-After
dates and bounds, concurrent cooldown changes, separate capacity/rendering deadlines,
backoff capacity release, extraction isolation, cancellation, cleanup, atomic publication
and completed JSONL retention. Local Chromium exercises real JavaScript, dynamic buttons,
redirect policy, third-party script rendering, transient recovery and selector timeouts.

Reproduce with the commands in [integration.md](integration.md). If using the development
browser cache, set `PLAYWRIGHT_BROWSERS_PATH` to `scraper/.uv-cache/playwright` first.

## Approved live validation

Only `https://scadable.com/` was authorized as a live target. The successful run occurred
on **2026-10-16, 23:59:33–23:59:51 UTC**, taking about 18 seconds.

Configuration: BestFirst, 3 pages, depth 1, global/competitor/hostname concurrency 1,
2-second document/discovery spacing, mandatory robots, 3 sitemap documents, 8 sitemap
HTTP requests, 45-second active attempts, 30-second discovery, and at most 2 retries.
No extra domains or dynamic rules were added.

The first launch failed before any HTTP request because the SDK's default home cache
was not writable. Setting `CRAWL4_AI_BASE_DIRECTORY` to the ignored local cache resolved
that. The sandbox then blocked robots retrieval; the guard failed closed and crawled no
pages. The approved run with network access succeeded without bypassing robots or TLS.

| Requested page | HTTP | Attempts | Category | Full / cleaned / filtered characters |
| --- | --- | --- | --- | --- |
| `/` | 200 | 1 | positioning | 5,468 / 5,468 / 2,913 |
| `/blog` | 200 | 1 | blog | 20,467 / 20,467 / 18,061 |
| `/blog/iso42001-ai-product-development` | 200 | 1 | products | 13,394 / 13,394 / 10,630 |

Requested and final URLs matched on all three pages. Titles, source links, UTC timestamps,
response metadata and all three Markdown representations were retained. The article's
`products` category illustrates keyword labeling of a mixed blog/product page; it is not
a semantic content classification.

Result: `run_status=success`, `completion_reason=page_limit`, **3 successful / 0 failed**.
The registry contains **80 unique discovered URLs**: 3 crawled, 66 deferred by the page
limit, 7 skipped and 4 relevant external URLs recorded without being crawled. Of those
records, 55 originated in sitemap discovery. There are no pending records or warnings;
`discovery_truncated=false`. `/sitemap.xml` returned 200; the conventional
`/sitemap_index.xml` fallback returned 404 and was handled normally.

Local artifacts are ignored by Git:

- `output/live-scadable.toml`: exact live configuration.
- `output/live-scadable.jsonl`: three typed page records and a validated summary.
- `output/live-scadable.json`: equivalent complete document, converted locally from
  JSONL without another website fetch and validated with `CrawlRunDocument`.

## Coverage limits

This small sample verifies the approved site's rendering/discovery pipeline. It does not
establish coverage of every competitor, every source category or arbitrary dynamic pages.
Priority is over known candidates; this sample selected blog content within the three-page
budget. The deferred registry makes remaining work visible. Live pages needed no retry;
retry and failure behavior were verified with controlled mocks and Chromium fixtures.
No anti-bot bypass, database, backend endpoint, LLM call or scheduler was introduced.

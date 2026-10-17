# Stage 4 reliability and integration plan

Historical stage plan. Current export/publication behavior is documented in
[output-layout.md](output-layout.md); prior generated artifacts remain preserved.

Goal: finish the standalone scraper's reliability, verification and integration docs.
Base: Stage 3 commit `f801e62`. Stage 4 design and live testing on
`https://scadable.com/` were explicitly approved. No commit until final review approval.

## Approved behavior

- Retry transient network/timeouts and HTTP 408/429/500/502/503/504 only, up to
  `max_retries` (default 2). Use exponential backoff/jitter, bounded by
  `max_backoff_seconds` (30). Honor Retry-After; stop rather than retry early when
  its requested wait exceeds the configured bound.
- One application owner for page retries; the HTTP reader owns its bounded discovery
  retries. SDK retries stay disabled. Page retries reuse the frontier reservation.
- Preserve `attempt_count` and diagnostic history in existing metadata; retain the
  version 1.0 schema and existing public component boundaries.
- Release page/hostname capacity during backoff. Bound capacity waits separately
  (default 120 seconds) from the 45-second active page-attempt budget. Redirect render
  hops share the active budget; cancellation always propagates.
- Isolate extraction failures per page, retaining sources and successful page results.
- Publish JSON files atomically; keep completed JSONL competitors on interruption.
- Improve progress/failure logging, fixture/browser tests, setup and integration docs.

## Test-first implementation tasks

- [x] Add retry policy tests, then `src/reliability.py`: failure classification,
  Retry-After parsing and exponential delay selection; verify HTTP/status/header edge cases.
- [x] Extend service/discovery/browser tests, then add page retry orchestration,
  bounded capacity/startup/cleanup and per-page extraction isolation. Verify budgets,
  backoff capacity release, attempt history, queue timeouts and cancellation.
- [x] Add HTTP reader retry tests, then extend `discovery/http.py`. Verify retries
  consume the existing HTTP budget, policy denials never retry, robots stay fail-closed,
  and Retry-After is respected without unbounded sleeps or redirect bypasses.
- [x] Add interrupted/error output tests, then implement atomic JSON publication and
  explicit async-iterator cleanup in the CLI. Preserve UTF-8 and existing JSONL schemas.
- [x] Expand local Chromium integration tests for transient HTTP errors, partial results,
  timeouts and resource cleanup. Keep all default tests offline.
- [x] Verify installation, lock/build, library API, both output formats and CLI entry point.
- [x] Run one approved live crawl of SCADABLE: max_pages=3, max_depth=1,
  max_concurrency=1, max_concurrent_competitors=1, per_domain_concurrency=1,
  request_delay_seconds=[2,2], mandatory robots, at most 3 sitemap documents and
  8 sitemap HTTP requests. Keep generated data in ignored output/. Report actual coverage,
  failures, deferred URLs and limits. Do not crawl any other live target.
- [x] Complete setup/reliability and backend/LLM consumption docs and verification report.
- [x] Run independent review and final tests; stop for user review before commit.

Verification: 241 tests passed with local Chromium enabled; default suite 234 passed,
7 skipped. Ruff lint/format, lock consistency, source/wheel builds, fresh wheel installation,
CLI and API/output smoke checks passed. Approved live crawl: 3 successful pages,
80 discovered URLs, 66 deferred, no warnings. See [validation.md](validation.md).
Final stage review and commit were explicitly approved by the user.

## Scope boundaries

No API server, persistence, LLM calls, frontend, scheduling, automatic change detection,
automatic resume or remote push. No new infrastructure. Public-site fetching and source
content only. Additional live domains require approval; rendering resources follow the
already approved third-party resource policy.

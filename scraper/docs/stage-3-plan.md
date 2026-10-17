# Stage 3 implementation plan

Goal: connect the approved shared discovery frontier to Crawl4AI rendering, conservative
content extraction, structured output and a multiple-homepage CLI. Stage 2 is committed
as `1d8e50e`. Files stay directly under `src/` in the installed `scraper` package.

## Approved design

- Allow third-party rendering resources; guard document navigation with exact-host and
  Protego robots policy. The application guard replaces duplicate SDK robots requests.
- Preserve full source Markdown unchanged, provide SDK filtered Markdown separately and
  conservatively normalize the full version for `cleaned_markdown`.
- First matching URL rule controls bounded CSS waits, scrolling and explicit load-more
  clicks. Pagination links enter the existing frontier and page/depth limits.
- One browser per active competitor; shared service page concurrency across competitors.
- JSON contains a versioned run document. JSONL contains typed pages followed by a
  summary for each competitor, without repeating page bodies in summaries.

## Browser policy detail

Playwright's normal routing does not re-intercept automatic redirect destinations (also
confirmed with a loopback probe). Document requests use public `route.fetch` with
`max_redirects=0` and no automatic retries. A redirect response is never fulfilled into
the browser: abort that navigation and run Crawl4AI on the checked destination instead.
Redirects consume the configured hop limit, not another distinct-page slot. Only the
expected main-page document may load; embedded documents, popups and unexpected document
navigations are blocked. CSS, scripts, images and fetch/XHR resources may load externally.
No iframe content is collected. Page service-worker bypass is enabled before navigation.

## Implementation and verification

Implementation follows test-first steps per component; tests run against the existing
code before implementation to establish the missing behavior, then run again afterwards.
No intermediate commits: stop for review and commit only on explicit stage approval.

- [x] Extraction: add `tests/unit/test_extraction.py`, then `src/extraction.py`.
  Verify unchanged raw/filtered content, Markdown tables/code, UTC/source metadata,
  keyword categories/ties, failed and empty pages; run the extraction test module.
- [x] Browser adapter: extend configuration tests and add browser-fetch tests, then
  `src/browser.py` and extend `src/crawl4ai_adapter.py`. Verify actual SDK result mapping,
  relative links, explicit dynamic rules, navigation/redirect denial before egress,
  deadlines and cleanup/cancellation. Use synthetic SDK fixtures and loopback servers.
- [x] Service: add `tests/unit/test_service.py`, then `src/service.py`. Compose the real
  discovery engine and injected fetcher/HTTP fixtures; verify per-competitor overrides,
  page failures, URL accounting, global concurrency and completed-result iteration.
- [x] Output: add output tests, then `src/output.py` and run-document/record models in
  `src/models.py`. Verify JSON round trips and JSONL page/summary reconstruction with
  derived counts, Unicode and no repeated page bodies.
- [x] CLI: add CLI tests, then `src/cli.py`, `src/__main__.py` and the console entry point.
  Verify multiple inputs, TOML matching, override precedence, malformed input and exit
  codes, stdout/stderr separation, output formats and refusal to overwrite by default.
- [x] Update README, architecture/config examples and Stage 3 usage documentation.
- [x] Run full pytest, Ruff lint/format, lock validation, build and installed CLI checks.
  Browser checks use loopback content only; live competitor testing requires Stage 4
  approval. Retry/backoff hardening and broader reliability remain Stage 4 scope.
- [x] Prepare deliverables, verification and limitations for the user review checkpoint.

## Verification evidence

- Full suite with local Chromium checks enabled: 178 passed, including five real-browser
  loopback tests. No live competitor website was contacted.
- Ruff lint and format checks pass. Lock validation and source/wheel builds pass.
- A separate environment installed the wheel and verified all 98 runtime packages are
  compatible. Imports and the console entry point work independently of the source tree.
- Independent read-only review found shared redirect-host limits and Windows stdout
  encoding issues. Regression tests reproduced both before fixing them. Shared
  `src/limits.py` hostname slots/pacing and UTF-8 stdout now address both; re-review found
  no new material issues. Cancellation, page deadlines and constructor cleanup are covered.
- Stage 3 remains uncommitted pending explicit user review approval.

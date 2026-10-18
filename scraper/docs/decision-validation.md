# Adaptive selection verification

## Offline scope

The Stage 3 suite exercises the real service, frontier, prompt builder, installed OpenAI
SDK adapter and bundle exporter. Website HTTP/rendering and OpenAI HTTP are mocked in
`tests/integration/test_decision_workflow.py`. The additional Chromium case in
`tests/integration/test_browser_local.py` renders a loopback website while keeping OpenAI
HTTP mocked. Inherited `OPENAI_API_KEY` values are removed by the test fixture; adapter
tests install a dummy key. No test requires a paid request or live competitor crawl.

The inspectable source fixture is
[`company_selection.json`](../tests/fixtures/company_selection.json). Its proposed labels
are scripted test answers on the 0–3 rubric, rather than measured model judgments:

| Scenario | Expected application behavior |
| --- | --- |
| Opaque `/a17` with descriptive platform link | Context reaches Decisions; a high returned score can prioritize it |
| Customer report and office/vacancy announcement | Company evidence can outrank generic articles at a four-page budget |
| Generic industry blog | Lower scores reduce priority; successful Markdown is still exported |
| Misleading `/pricing` link | Content assessment can return `other` and low usefulness despite a promising link |
| Duplicate platform description | Both source files survive; repeated evidence does not inflate the ledger |
| Prompt-injection text | Text is evidence under an explicit policy; answers cannot invent URLs or override scope |
| High-scored robots-denied URL | Robots enforcement prevents fetching and releases the page/schedule reservation |
| Unapproved external link | Recorded, never scheduled as a candidate or fetched |
| HTTP 503 / exhausted allowance | Structural fallback, retained Markdown, usage diagnostics and a warning |

These tests verify data flow and controls with deterministic answers. They do **not**
prove that a live model will reject every misleading/injected instruction, improve
relevance, or meet a particular latency/cost target. Domain/robots/limit enforcement is
owned by the application regardless of returned scores.

Exporter tests cover trace opt-in, empty traces, UTF-8 round trips, safe fixed references,
staging/publication failures and summary-last ordering. CLI tests check sparse nested
overrides and invalid allowances. Existing suites cover retries, refusals, malformed
answers, cancellation, independent budgets, scoring caches, BFS, exploration schedules
and structural mode without API calls.

From `scraper/`:

```powershell
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Get-Location) ".uv-cache/playwright"
$env:SCRAPER_BROWSER_TESTS = "1"
uv run --locked pytest tests/integration/test_browser_local.py -q
```

## Stage 3 verification results

Verified October 18, 2026, against Stage 2 base `f97af15` plus the Stage 3 working tree:

- Default suite: **376 passed, 8 browser cases skipped** in 21.32 seconds.
- Full suite including loopback Chromium: **384 passed** in 41.95 seconds.
- Ruff lint and formatting: passed (75 Python files).
- `uv lock --check --offline --cache-dir .uv-cache`: passed.
- Offline source/wheel build: passed. An isolated Python process imported this build's
  wheel, validated the schema `2.1` sample and nine trace records, and checked new CLI flags.
- `git diff --check`: passed.
- Independent read-only review: no Critical, Important or Minor findings; its targeted
  output/CLI/manual-runner/SDK-workflow run passed 57 tests.

A concrete mocked review bundle is at
`output/decisions-review-20261018-215211-904015/example.com/`: eight Markdown files,
`crawl_summary.json`, and nine `decisions.jsonl` records. It is ignored generated data.
Its input usage and estimated cost are scripted fixture values, not actual API usage.
The first sample attempt needed the documented writable SDK cache setting; the successful
sample used `CRAWL4_AI_BASE_DIRECTORY=.uv-cache`. No runtime change was necessary.

Stage 3 is ready for user review and remains uncommitted pending explicit approval.

## Live pilot: approval required, not run

Historical permission for the original scraper's live crawl is not approval for paid
Decisions calls. A new pilot needs approval of the website and limits before execution.
Start with one homepage, three pages, depth one, browser/competitor/domain concurrency
one, at least two seconds between page starts, a $0.03 estimated allowance and tracing
enabled. Keep robots and the existing bounded sitemap limits enabled. Increase the page
budget only after reviewing the small run; use at least six pages to observe the default
first exploration attempt.

Compare two fresh bundles at equal page/depth/request limits and the same website state:
the LLM-guided implementation and a separate checkout of the recorded legacy keyword
revision (`26ffd41`). Record that revision and resolved settings; do not reintroduce
keyword scoring into production or treat structural mode as the old keyword baseline.
Use separate fresh output roots. Record sitemap changes or unavailable pages that weaken
comparability; timing a live site cannot guarantee identical conditions.

Review the collected source Markdown manually against the objective before looking at
model scores. Label each successful page as direct company evidence, generic/redundant
material, or unavailable, and record which offerings/customer/differentiation/commercial/
expansion themes are supported by source-linked excerpts. Compare useful distinct pages
per equal attempt budget and thematic coverage; do not score a page using only its URL.

Record total crawl duration, successful/failed/attempted counts, API attempt latency
(sum and range from the trace), request count, model/prompt version, reported input usage,
uncertain reservations, estimated cost and fallback events. Compare reported usage with
the provider's billing/usage view separately: estimates are not invoice verification.
An interrupted/failed request may remain uncertain. Report findings and source URLs,
including disappointing results; do not infer future growth from collection quality.

Pilot acceptance is a review decision: useful company-evidence coverage should improve
or remain comparable without losing source provenance or exceeding acceptable latency.
Assess the user's under-$0.10 target using observed usage, with the tighter $0.03
application allowance as the initial setting. No empirical quality, cost, or latency
claim is made until this paid comparison is approved and run.

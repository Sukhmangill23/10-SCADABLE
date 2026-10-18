# OpenAI Decisions — Stage 1 foundation

This stage provides the configuration, typed contracts, API adapter, and budget accounting
for the approved OpenAI-guided selection plan. **The adapter is not connected to the
existing crawl service yet.** Running the CLI or manual runner still uses the existing
keyword workflow until Stage 2. The new selection settings currently configure the adapter
only; they do not change traversal by themselves.

Stage 2 will connect adaptive selection, remove keyword settings with explicit migration
errors, and consume content assessments for page categories. Stage 3 will add summary
diagnostics, trace-file publication, CLI/manual-runner controls, and integration guidance.
Schema versions remain unchanged in this intermediate stage; their planned bumps accompany
integration/output changes. No paid requests or live crawls are required to review Stage 1.

## Configuration and public boundary

`SelectionConfig`, also available as `ScraperConfig.selection`, contains:

| Setting | Default |
| --- | --- |
| `mode` | `llm`; alternative `structural` |
| `model` | `gpt-6-luna` |
| `objective` | Company-specific offerings, customers, differentiation, commercial activity, and observable expansion/contraction evidence |
| `budget_usd` | `0.03` per competitor |
| `exploration_fraction` | `0.20`; selection scheduling is implemented in Stage 2 |
| `trace_enabled` | `false` |
| `timeout_seconds` | `15` per API attempt |
| `max_retries` | `2` additional attempts |
| `max_concurrency` | `2`; service integration will supply the shared run-wide ceiling |

Settings merge using existing defaults < global < competitor < CLI precedence, preserving
partial nested overrides. The objective accepts up to 4,000 characters. Credentials are
not configuration fields and never appear in serialized settings.

`DecisionProvider` is the SDK-independent injection interface in `interfaces.py`:

- `score_candidates(candidates)` returns a result for each supplied candidate, in input order.
  Results distinguish scored, refused, invalid, and unavailable answers. SDK score levels
  0–3 are normalized to 0–1; a refusal or invalid answer never becomes a zero score.
- `assess_content(page, ledger=())` returns independent usefulness, novelty, and category
  results. A refused/invalid question does not discard valid answers to other questions.
- `summary` returns a snapshot of mode, usage, cost estimate, and fallback events.
- `trace_records` returns defensive copies of bounded in-memory traces when enabled.
- Providers are asynchronous context managers and belong to exactly one competitor crawl.

`OpenAIDecisionProvider` owns an `AsyncOpenAI` client. An optional shared semaphore allows
different competitors to share API capacity while keeping budgets separate. The provider
never starts Crawl4AI, navigates URLs, or owns browser capacity.

Evidence models bound observations to 160 characters of anchor text, 160 of heading, and
400 of surrounding text, with at most two observations per candidate. The upstream context
builder arrives in Stage 2. The adapter groups at most 50 candidates within a 48 KiB
serialized-request bound, includes at most 6,000 sampled Markdown characters, and accepts
at most eight ledger excerpts per request, each bounded to 500 characters. Gaps between
sampled page sections are marked explicitly. Full page Markdown is never changed.

## Credentials, failures, and estimated costs

The LLM provider requires `OPENAI_API_KEY` before creating its SDK client. Structural mode
requires no key, creates no SDK client, and makes no API requests. The service's pre-browser
credential check will be wired in Stage 2; merely importing configuration reads no keys.

The SDK's automatic retries are disabled. The adapter retries connection failures/timeouts
and HTTP 408/429/500/502/503/504 only, up to the configured limit. Retry-After is honored;
delays above 30 seconds activate structural fallback instead of retrying early. Shared API
capacity is released before backoff. HTTP 401/403 raise sanitized `DecisionAccessError`
exceptions and do not silently fall back.

At the documented Decisions base rate of **$0.10 per million input tokens**, $0.03 corresponds
to 300,000 tokens. Before every attempt, the budget reserves serialized UTF-8 request bytes
plus 1,024 tokens for overhead. Returned usage replaces that reservation. Requests with
unknown usage, including interrupted requests, retain their full estimate in a separate
uncertain-usage counter. Retries reserve again; waiting for shared capacity reserves nothing.

This deliberately conservative estimate is **not a guaranteed invoice ceiling**. It does
not claim cache discounts and excludes regional/long-context adjustments. Reported input
usage can also exceed a reservation; any overrun is accounted and blocks subsequent calls.
No free-form generated explanations, summaries, or separate Responses API calls are used.

Budget exhaustion, persistent transient failures, and malformed response envelopes disable
further API requests for that provider. Its summary records a single structural fallback
event. The adapter reports outcomes; continuing the crawl structurally is Stage 2's job.

Enabled traces contain request evidence, validated answers, timing, and token accounting.
SDK exception bodies/messages, authorization headers, and API keys are not recorded.
Stage 1 retains traces in memory; Stage 3 will publish `decisions.jsonl` when requested.

Official references, verified October 18, 2026:

- [Decisions guide and pricing](https://developers.openai.com/api/docs/guides/decisions)
- [Python request/response reference](https://developers.openai.com/api/reference/python/resources/decisions/methods/create)

## Review without paid requests

From the `scraper` directory, use the existing project environment:

```powershell
uv sync --locked --offline --cache-dir .uv-cache
.\.venv\Scripts\python.exe -m pytest tests/unit/test_selection_contracts.py tests/unit/test_decision_budget.py tests/unit/test_decisions.py -q
.\.venv\Scripts\python.exe -m pytest tests/unit -q
```

The adapter tests use injected SDK stubs and the installed SDK with a mock HTTP transport.
They do not contact OpenAI or websites and do not need a real API key. The OpenAI SDK is
now a direct dependency (`openai>=3.26,<4`); the existing locked 3.32.0 version is retained.

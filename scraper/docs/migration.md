# Migrating to adaptive selection

## Configuration and credentials

LLM selection is now the default. Install the locked dependencies with `uv sync --locked`
and put `OPENAI_API_KEY=your-openai-api-key` in a local `.env` copied from `.env.example`.
The CLI loads the working directory's file or `--env-file`; the manual runner loads the
file beside `manual_test.py`. Existing process environment values take precedence.
Python consumers can explicitly call `scraper.environment.load_environment(path)`.
Missing credentials fail before
browser/network activity. Choose explicit structural mode for crawling without OpenAI:

```python
from scraper import ScraperConfig, SelectionConfig

settings = ScraperConfig(
    selection=SelectionConfig(mode="structural"),
)
```

Or use `--selection-mode structural`, or TOML:

```toml
[global.selection]
mode = "structural"
```

Remove these obsolete fields wherever they appear in global or per-competitor settings:

| Removed field | Replacement |
| --- | --- |
| `category_keywords` | Content assessment supplies categories; unavailable assessments use `other` |
| `minimum_relevance_score` | Low scores affect order; they no longer exclude eligible URLs |
| `url_keyword_weight` | Use `selection.objective` to describe the research goal |
| `title_keyword_weight` | Link context and fetched content inform model scores |

`_default_keywords` and keyword category maps were implementation helpers and have been
removed. Validation names obsolete fields with replacement guidance; they are never
silently accepted. The old public keyword map had been named `category_keywords`.

All existing page/depth, scope, robots, request and dynamic-page settings retain their
behavior. Nested selection overrides merge defaults < global < competitor < CLI;
omitted CLI flags do not overwrite TOML. `--decision-trace` and `--no-decision-trace`
explicitly enable/disable trace export. BFS skips candidate scoring but still assesses
content in LLM mode; structural mode disables both decision operations.

## In-memory schema 1.0 to 1.1

`CompetitorCrawlResult.schema_version` is `1.1`. Additions include:

- Pages: optional typed `content_assessment` and `selection`.
- Competitor: optional `decision_usage` and an opt-in `decision_trace` list.
- Discovery: nullable relevance scores and bounded contextual link observations.

Full source, filtered and cleaned Markdown remain available. Page categories now come
from content assessment, or `other` when unavailable. They are model labels rather than
verified company facts. Low-value and duplicate successful content is still retained.

Strict consumers must update their accepted version and model fields. Old in-memory
snapshots can be read with their previous schema/model; this package does not silently
rewrite snapshots or infer missing assessments.

## Export schema 2.0 to 2.1

Markdown paths and content are unchanged. `crawl_summary.json` remains the completion
marker. Schema `2.1` adds:

| Field | Meaning |
| --- | --- |
| `pages[].selection` | Method, available relevance score and assessment availability |
| `decision_usage` | Requested/effective modes, model/prompt version, usage, cost estimate and fallback events |
| `decision_trace_file` | Optional fixed relative path `decisions.jsonl` |

Optional diagnostics are omitted for custom results that do not supply them. Tracing is
off by default. Enabling it writes a UTF-8 JSONL record per dispatched attempt, or an empty
file when nothing was dispatched. It includes bounded website evidence; the summary
does not. Keys, authorization headers and SDK error bodies are not exported.

Update readers that reject unknown fields or require version `2.0`. The current
`CrawlExportSummary` accepts `2.1` only; retain a versioned legacy reader for old exports
and dispatch using `schema_version`. Do not relabel a historical file to imply it contains
new diagnostics. Existing files remain untouched; reruns require a fresh output directory.

`decision_usage.estimated_cost_usd` includes reported input plus uncertain reservations
at the configured adapter's base rate. It is an application estimate, not an invoice or
guaranteed spending cap. Budget/API fallback can leave `status="success"` when collection
succeeded: inspect effective mode, fallback events and warnings separately.

See [quickstart.md](quickstart.md) for editable runs and [integration.md](integration.md)
for typed consumers. No backend, database or downstream analysis changes are required.

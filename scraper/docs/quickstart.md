# Quickstart: setup, crawl and inspect results

## How it works

You provide homepage URLs. For each competitor, the scraper checks robots.txt, renders
the homepage with Crawl4AI, reads bounded sitemaps and discovers internal links. One
shared frontier scores bounded link context with OpenAI Decisions and chooses subsequent
pages using BestFirst plus exploration (or BFS). Default limits are 50 pages and depth 3.

Each fetched page contributes Markdown, metadata and more links. The extractor preserves
full source Markdown, creates a conservative cleaned version and consumes content-based
categories. Transient failures get bounded retries. The result contains page outcomes
plus a URL registry explaining what was skipped, deferred or external.

External document domains require explicit approval/configuration; relevant external
links are recorded. Third-party resources needed for rendering are allowed. The scraper
runs independently of the backend, database and downstream company analysis.

Default LLM crawling reads `OPENAI_API_KEY` from your local `.env` file. It scores discovered links from their URL
and nearby text, then assesses fetched excerpts for usefulness, novelty and category.
The estimated allowance is $0.03 **per website**, with structural fallback when exhausted;
it is not a guaranteed billing ceiling. See [decisions.md](decisions.md) for accounting.
Explicit structural mode makes no OpenAI calls and uses category `other`.

## Set up on Windows

Install Python 3.12 and uv first. Run these commands in PowerShell from the repository
root. Installation and offline tests need no virtual-environment activation or API key:

```powershell
cd scraper
$env:UV_CACHE_DIR = Join-Path (Get-Location) ".uv-cache"
$env:CRAWL4_AI_BASE_DIRECTORY = Join-Path (Get-Location) ".uv-cache"
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Get-Location) ".uv-cache\playwright"
uv sync --locked
uv run --locked python -m playwright install chromium
uv run --locked scraper --help
```

Run the three environment-variable assignments again in a new terminal. They keep SDK
and browser caches in a writable, ignored project directory. The same browser path must
be used for installation and execution. All commands below run from `scraper/`.

## Run an editable Python file

Open [manual_test.py](../manual_test.py) and edit the values at the top:

- `WEBSITES`: homepage URLs and optional competitor names; add an entry per website.
- `SETTINGS`: page/depth limits, concurrency, request spacing and sitemap bounds.
- `SETTINGS.selection`: `mode` (`llm` or `structural`), `objective`, `budget_usd`, and
  `trace_enabled` (save request evidence and answers for review).
- `OUTPUT_DIRECTORY`: defaults to a readable UTC folder under `output/`, such as
  `manual-2026-10-18_23-26-46_UTC`. Runs started within the same second share a name;
  an existing folder is refused, so wait a second or choose a different name.

Start with one website and `max_pages=3`. For LLM mode, open `scraper/.env` in your editor
and enter your key after `=`:

```dotenv
OPENAI_API_KEY=your-openai-api-key
```

If `.env` does not exist in a fresh checkout, copy `.env.example` to `.env` first.
The file is ignored by Git. Existing process environment values take precedence.
You do not need to enter the key in the terminal. Run the editable file from `scraper/`:

```powershell
uv run --locked python manual_test.py
```

To make an API-free manual run, edit `mode="structural"` in the Python file; no key is
needed. Keep credentials in `.env`, outside the Python/TOML settings.

You can also select the project's `.venv` Python interpreter in VS Code and run the file
using **Run Python File**, or execute `.venv/Scripts/python.exe manual_test.py` directly.
The runner loads `.env` beside `manual_test.py` regardless of your working directory.
It configures the SDK cache and detects the local browser cache automatically;
explicit environment settings take precedence. Paths are relative to the script's project
directory, so changing your terminal's working directory does not move the output.

The log shows the exact output directory, each saved `crawl_summary.json`, selection mode
and estimated usage cost. Markdown
files are under each website's `pages/` directory. A fixed custom output directory must
be new; existing output is never replaced. The tests for this runner mock crawling;
executing the runner itself contacts the configured websites.

## Alternative: manual CLI test

Start with a small crawl. Replace `https://competitor.example/` below with a homepage
you are authorized to crawl. This creates an ignored local configuration:

```powershell
New-Item -ItemType Directory -Force output | Out-Null
@'
[global]
max_pages = 3
max_depth = 1
max_concurrency = 1
max_concurrent_competitors = 1
per_domain_concurrency = 1
request_delay_seconds = [2.0, 2.0]
max_sitemap_documents = 3
max_sitemap_requests = 8

[global.selection]
mode = "llm"
budget_usd = 0.03
trace_enabled = false

[[competitors]]
homepage_url = "https://competitor.example/"
name = "Example competitor"
'@ | Set-Content -Encoding ascii output/manual.toml

uv run --locked scraper --config output/manual.toml --output output/run-001
```

The CLI loads `.env` from its working directory. When launching it elsewhere, pass
`--env-file C:/path/to/scraper/.env`. An explicitly supplied file must exist. Neither
entry point searches parent directories for credentials. The manual runner always uses
its own project directory, while CLI paths are relative to the current working directory.

Progress logs include each saved index path. Each competitor gets a directory containing
`crawl_summary.json` and readable Markdown files under `pages/`. An existing competitor
directory is refused; choose a fresh run root such as `output/run-002` for a repeat crawl.

## See the output

Open `output/run-001/competitor.example/pages/index.md` in your editor. Each subpage
has its own Markdown file, such as `pages/pricing.md` or `pages/products/analytics.md`.
Substitute the actual hostname you configured for `competitor.example`.

Open `crawl_summary.json` beside `pages/` to see the index, or inspect it in PowerShell:

```powershell
$site = "output/run-001/competitor.example"
$summary = Get-Content "$site/crawl_summary.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$summary.counts
$summary.completion_reason
$summary.pages | Select-Object url, markdown_file, title, category, status, word_count
$page = $summary.pages | Where-Object status -eq 'success' | Select-Object -First 1
Get-Content (Join-Path $site $page.markdown_file) -Raw -Encoding UTF8
$summary.uncrawled_urls | Where-Object status -eq 'deferred' | Select-Object url, reason
$summary.decision_usage
$summary.pages | Select-Object url, selection
```

Schema `2.1` adds per-page `selection` and competitor `decision_usage`. Compare
`requested_mode` and `effective_mode`, check `fallback_events`, and distinguish
`reported_input_tokens` from conservative `uncertain_input_tokens`. The latter covers
dispatched requests whose actual usage could not be recovered.

Enable `trace_enabled=True` in the manual runner or pass `--decision-trace` in the CLI
to save `decisions.jsonl`. Its path appears in `decision_trace_file`; it contains bounded
website evidence, validated answers, timings and accounting. To inspect it:

```powershell
if ($summary.decision_trace_file) {
    Get-Content (Join-Path $site $summary.decision_trace_file) -Encoding UTF8 |
        ForEach-Object { $_ | ConvertFrom-Json } |
        Select-Object operation, attempt, duration_seconds, reported_input_tokens, error_code
}
```

An enabled trace can be empty when no decision was dispatched. With tracing disabled,
the file and reference are absent. Normal summary JSON contains no request evidence.

| Field | Meaning |
| --- | --- |
| `markdown_file` | Content-only Markdown path, relative to the summary's directory |
| `url` / `final_url` | Requested source; final URL is included when redirected |
| `title` / `category` | Page title and content-based category (`other` if unassessed) |
| `status` / `error` | Success or failure; failed pages have no Markdown file |
| `discovered_from` / `discovery_sources` | Recorded parents and discovery methods |
| `depth` / `depth_basis` | Traversal depth, or logical sitemap-seed depth |
| `uncrawled_urls` | Skipped, deferred, external or pending URLs and reasons |
| `selection` | Selection method, available relevance score, assessment availability |
| `decision_usage` | Requested/effective modes, model/prompt version, usage, estimate and fallbacks |

The JSON contains no page bodies, response headers or full configuration. It is a compact
index for readers and downstream code. Every successful page's conservative cleaned
Markdown is preserved in its referenced file. Full source/filtered content remains
available through the Python API.

`status=success` means collection succeeded; `completion_reason=page_limit` means the
budget stopped traversal. It does not mean the whole site was read. Require a
`crawl_summary.json` before accepting a competitor export; completed competitors survive
later interruption. A partial publication may leave a folder without that marker.

Generated data is ignored by Git. See [output-layout.md](output-layout.md) for naming,
collision rules and an example entry. The old JSON/JSONL formats and `--format`,
`--overwrite`, `--output -` options were replaced by this directory format; existing
historical crawl data remains untouched.

## More websites and configuration

For multiple competitors, add more `[[competitors]]` sections to the TOML file. Add
`[competitors.overrides]` after a competitor to customize its settings. See
[config.example.toml](../config.example.toml) for the complete pattern and dynamic rules.
Inputs are homepages with `http://` or `https://`, not individual article URLs.

Common overrides:

```powershell
uv run --locked scraper --config output/manual.toml --max-pages 10 --max-depth 2 --output output/larger-run
uv run --locked scraper --config output/manual.toml --strategy bfs --output output/bfs-run
uv run --locked scraper --config output/manual.toml --selection-mode structural --output output/no-api-run
uv run --locked scraper --config output/manual.toml --decision-budget-usd 0.01 --decision-trace --output output/traced-run
```

`--research-objective "Customer wins and product capabilities"` changes the selection
objective. `--no-decision-trace` overrides enabled tracing in TOML. BFS skips candidate
scoring but still assesses fetched content in LLM mode; combine BFS with structural mode
to disable all decision requests. All other selection controls are in Python/TOML.

CLI options override competitor settings, which override global settings and defaults.
Keep crawl budgets small while checking content quality. Add specific CSS waits or
bounded scrolling/load-more rules for websites that need them; the scraper does not
guess arbitrary pagination controls.

New crawls omit semantic navigation and site footers from Markdown while keeping their
links available for page discovery. Article headers and attribution are preserved.
For menus/footers built with generic `<div>` elements, add the site's actual CSS selectors
in the manual runner's `SETTINGS`, or in the corresponding TOML override:

```python
from scraper import ScraperConfig

settings = ScraperConfig(
    markdown_remove_navigation_and_footer=True,
    markdown_excluded_selectors=[".site-menu", ".site-footer"],
)
```

Those class names are examples; inspect the website's HTML for the correct containers.
Set the flag to `False` and the list to `[]` to retain all navigation/footer content.
Existing generated Markdown stays unchanged. See
[extraction and output](extraction-and-output.md#navigation-and-footer-removal) for details.

## Tests and troubleshooting

```powershell
uv run --locked pytest -q
uv run --locked ruff check .
$env:SCRAPER_BROWSER_TESTS = "1"
uv run --locked pytest tests/integration/test_browser_local.py -q
```

Default tests are offline. Opt-in browser tests use local fixture servers. They do not
crawl live competitor websites.

- Missing Chromium: repeat the browser-install command using the same browser path.
- SDK cache permission error: set `CRAWL4_AI_BASE_DIRECTORY` before starting Python.
- Robots or network failure: inspect `warnings`, deferred reasons and page errors.
  Robots checks fail closed; an unavailable robots file can prevent page collection.
- Failed page: inspect its `error`, optional HTTP status/retry fields and logs;
  add `--verbose` for more detail. Other competitors continue.
- Existing competitor directory: choose a fresh `--output` root for the next run.
- Missing API key: fill in `OPENAI_API_KEY` in `.env`, select the correct `--env-file`,
  or choose structural mode before crawling.
- HTTP 401/403 from Decisions: check the key and project/model access. The affected
  competitor stops and retains collected pages. Budget or transient API fallback is a
  warning; it does not make successfully scraped pages fail.

Exit codes are 0 for successful collection, 1 for a partial/failed competitor, 2 for
input/output errors and 130 for interruption. In PowerShell, inspect `$LASTEXITCODE`
immediately after the CLI command.

For importing the asynchronous service or reading validated summary/Markdown bundles,
see [integration.md](integration.md).
For upgrading old configuration or strict summary readers, see [migration.md](migration.md).

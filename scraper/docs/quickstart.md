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

**Selection update:** default LLM crawling now requires `OPENAI_API_KEY`. Set it in your
environment before running. To crawl without API requests, add
`selection={"mode": "structural"}` to `ScraperConfig(...)` or add a TOML section
`[global.selection]` with `mode="structural"`. Structural pages use category `other`.
See [decisions.md](decisions.md) for the $0.03 estimated allowance and structural fallback.

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
- `OUTPUT_DIRECTORY`: defaults to a fresh timestamped folder under `output/`.

After the one-time setup above, run it from `scraper/`:

```powershell
uv run --locked python manual_test.py
```

You can also select the project's `.venv` Python interpreter in VS Code and run the file
using **Run Python File**, or execute `.venv/Scripts/python.exe manual_test.py` directly.
The runner configures the SDK cache and detects the local browser cache automatically;
explicit environment settings take precedence. Paths are relative to the script's project
directory, so changing your terminal's working directory does not move the output.

The log shows the exact output directory and each saved `crawl_summary.json`. Markdown
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

[[competitors]]
homepage_url = "https://scadable.com/"
name = "Example competitor"
'@ | Set-Content -Encoding ascii output/manual.toml

uv run --locked scraper --config output/manual.toml --output output/run-001
```

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
$summary.uncrawled_urls | Where-Object status -eq 'deferred' | Select-Object url, reason=
```

| Field | Meaning |
| --- | --- |
| `markdown_file` | Content-only Markdown path, relative to the summary's directory |
| `url` / `final_url` | Requested source; final URL is included when redirected |
| `title` / `category` | Page title and content-based category (`other` if unassessed) |
| `status` / `error` | Success or failure; failed pages have no Markdown file |
| `discovered_from` / `discovery_sources` | Recorded parents and discovery methods |
| `depth` / `depth_basis` | Traversal depth, or logical sitemap-seed depth |
| `uncrawled_urls` | Skipped, deferred, external or pending URLs and reasons |

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
```

CLI options override competitor settings, which override global settings and defaults.
Keep crawl budgets small while checking content quality. Add specific CSS waits or
bounded scrolling/load-more rules for websites that need them; the scraper does not
guess arbitrary pagination controls.

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

Exit codes are 0 for successful collection, 1 for a partial/failed competitor, 2 for
input/output errors and 130 for interruption. In PowerShell, inspect `$LASTEXITCODE`
immediately after the CLI command.

For importing the asynchronous service or reading validated summary/Markdown bundles,
see [integration.md](integration.md).

# Quickstart: setup, crawl and inspect results

## How it works

You provide homepage URLs. For each competitor, the scraper checks robots.txt, renders
the homepage with Crawl4AI, reads bounded sitemaps and discovers internal links. One
shared frontier scores known URLs using configured category keywords and chooses the
next pages with BestFirst (or BFS). Default limits are 50 distinct pages and depth 3.

Each fetched page contributes Markdown, metadata and more links. The extractor preserves
full source Markdown, creates a conservative cleaned version and assigns a keyword
category. Transient failures get bounded retries. The result contains page outcomes
plus a URL registry explaining what was skipped, deferred or external.

External document domains require explicit approval/configuration; relevant external
links are recorded. Third-party resources needed for rendering are allowed. The scraper
runs independently of the backend, database and LLM.

## Set up on Windows

Install Python 3.12 and uv first. Run these commands in PowerShell from the repository
root. No virtual-environment activation or API keys are required:

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

## First manual website test

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
homepage_url = "https://competitor.example/"
name = "Example competitor"
'@ | Set-Content -Encoding ascii output/manual.toml

uv run --locked scraper --config output/manual.toml --output output/manual.json
```

You will see progress logs in the terminal. The JSON file appears when the run finishes.
Existing output requires `--overwrite`; otherwise choose a new filename.

## See the output

Open `output/manual.json` in your editor, or inspect it with PowerShell:

```powershell
$run = Get-Content output/manual.json -Raw -Encoding UTF8 | ConvertFrom-Json
$result = $run.results[0]
$result.summary
$result.completion_reason
$result.pages | Select-Object source_url, page_title, page_category, crawl_status, http_status, attempt_count
$result.pages[0].cleaned_markdown
$result.discovered_urls | Where-Object disposition -eq 'deferred' | Select-Object url, reason
```

For readable Markdown in your editor:

```powershell
$result.pages[0].cleaned_markdown | Set-Content -Encoding utf8 output/first-page.md
```

| Field | Meaning |
| --- | --- |
| `raw_markdown` | Full SDK Markdown from rendered HTML, retaining source links |
| `cleaned_markdown` | Conservatively normalized full Markdown; usual analysis input |
| `filtered_markdown` | Optional SDK-filtered content; it can omit useful details |
| `source_url` / `final_url` | Requested source and final URL after redirects |
| `crawl_status` / `error_message` | Page success or failure and its explanation |
| `metadata.crawl_diagnostics` | Attempt history and why retries stopped |
| `discovered_urls` | Unique observed URLs, their provenance, disposition and reason |

`run_status=success` means page collection succeeded. `completion_reason=page_limit`
means the configured budget stopped traversal; it does not mean the whole site was read.
Keyword categories are coarse labels, so a product-focused blog article can be `products`.

Generated data is ignored by Git and is not included in a fresh clone.
See [validation.md](validation.md) for the existing live sample's paths and measured coverage.

## JSONL, more websites and configuration

Choose JSONL for one JSON object per line. Page records are followed by a competitor
summary; each completed competitor is flushed:

```powershell
uv run --locked scraper --config output/manual.toml --format jsonl --output output/manual.jsonl
Get-Content output/manual.jsonl -Encoding UTF8 | ForEach-Object { $_ | ConvertFrom-Json } | Select-Object record_type
```

Both commands crawl again; changing the output format is not a local conversion. JSON
files publish atomically. JSONL retains earlier completed competitors on Ctrl+C; require
a summary record before accepting that competitor as complete.

For multiple competitors, add more `[[competitors]]` sections to the TOML file. Add
`[competitors.overrides]` after a competitor to customize its settings. See
[config.example.toml](../config.example.toml) for the complete pattern and dynamic rules.
Inputs are homepages with `http://` or `https://`, not individual article URLs.

Common overrides:

```powershell
uv run --locked scraper --config output/manual.toml --max-pages 10 --max-depth 2 --output output/larger.json
uv run --locked scraper --config output/manual.toml --strategy bfs --output output/bfs.json
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
- Failed page: inspect `error_message` and `metadata.crawl_diagnostics`; add `--verbose`
  to see more logs. Other competitors continue.
- Reusing filenames: choose a new output path or explicitly pass `--overwrite`.

Exit codes are 0 for successful collection, 1 for a partial/failed competitor, 2 for
input/output errors and 130 for interruption. In PowerShell, inspect `$LASTEXITCODE`
immediately after the CLI command.

For importing the asynchronous service into another application or validating JSONL,
see [integration.md](integration.md).

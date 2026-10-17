# Output refactor verification

Base: `290f4e5`. The user approved the Markdown-plus-summary format, directory-based CLI
and fresh output directories for repeat runs. The implementation was reviewed and its
focused Git commit was explicitly approved. No remote push was performed.

## Requirements and evidence

| Requirement | Evidence |
| --- | --- |
| One content-only Markdown file per successful page | Tests compare files with exact `cleaned_markdown`; failed pages create no file |
| URL hierarchy and naming conflicts | Tests cover homepages, nested paths, queries, trailing slashes, case collisions, reserved names, long/unsafe segments, duplicate identities and file/directory conflicts |
| Concise per-competitor JSON | Schema `2.0` validates counts and references; tests exclude content bodies and raw metadata |
| Identity, UTC timestamps, timing, title/category, word count and status | Export tests and real loopback CLI test; service adds elapsed fetch timing metadata only |
| Discovery and uncrawled provenance | Tests preserve multiple parents, source methods, sitemap depth/basis and uncrawled reasons |
| Multiple websites and Python integration | CLI tests and fresh installed-wheel API smoke test process two competitors |
| Crawl behavior preserved | Only output contracts/writers/CLI change; service adds two timing lines; existing crawl suites pass |
| Preserve existing data and completed exports | Tests cover preflight refusal, concurrent directory creation, disk errors, staging/publication failures and interruption |
| Documentation and migration | README, quickstart, integration, architecture and extraction/output docs updated; obsolete file writers/record models and CLI flags removed |

## Verification results

- Full suite including local Chromium: **264 passed in 38.89 seconds**.
- Ruff lint/format, lock consistency and Git diff whitespace checks passed.
- Source distribution and wheel built offline into ignored `output/bundle-dist/`.
- A fresh wheel install in `output/bundle-venv/` verified imports came from that wheel,
  processed two mocked competitors, exported exact Markdown and validated compact
  summaries. Both installed CLI entry points displayed directory-based output help.
- Independent read-only review found two Windows path issues, fixed with red/green
  regressions: reserved basenames with extensions and synthetic secondary-host directory
  collisions. Re-review found no remaining material schema/path issues.

Reproduce from `scraper/` using the browser path used at installation:

```powershell
$env:SCRAPER_BROWSER_TESTS = "1"
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Get-Location) ".uv-cache\playwright"
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
uv lock --check
uv build
```

Default tests remain offline. Opt-in Chromium tests use local fixture servers.
No new live website request was made for this refactor.

## Review artifacts

Ignored `output/format-review/` contains:

```text
competitor-a.example/
  crawl_summary.json
  pages/index.md
  pages/pricing.md
competitor-b.example/
  crawl_summary.json
  pages/index.md
scadable.com/
  crawl_summary.json
  pages/index.md
  pages/blog.md
  pages/blog/iso42001-ai-product-development.md
```

The first two competitors are synthetic review fixtures. The third was exported locally
from the already-collected `output/live-scadable.json`, without refetching anything.
All three indexes validate and reference six Markdown files. The retained live result
still has 3 successful pages, 80 discovered URLs, 66 deferred, 7 skipped and 4 external
URLs. Original generated files remain untouched.

Open `competitor-a.example/pages/pricing.md` beside its `crawl_summary.json` entry for
a compact example: 7 word tokens, relative content path, source URL, category, timing
and homepage discovery relationship.

## Practical limits

`crawl_summary.json` is the completion marker; multi-file publication is not one filesystem
transaction. Publication failure can leave a directory without that marker; completed
competitors remain valid. Reruns require a fresh output root. Discovery relationships
reflect bounded recorded evidence, not an exhaustive link graph. See
[output-layout.md](output-layout.md) for the complete format.

# Stage 1 implementation plan

Goal: create a separately installable Python foundation with validated configuration,
source-linked result contracts, and testable boundaries for the approved shared-frontier design.

Architecture: the service will own the frontier, policy and budgets; a Crawl4AI adapter will
own SDK/browser interaction. Extraction and output consume application models rather than
SDK internals. This stage implements contracts and SDK configuration only.

Stack: Python 3.12, Crawl4AI, Pydantic v2, TOML, uv, pytest/pytest-asyncio and Ruff.
The approved specification is recorded in `architecture.md` in this directory.

Constraints: preserve existing repository files; use the existing scraper branch; no external
website crawls, backend, database, LLM, CLI execution, or traversal implementation in Stage 1.
No commit until the user reviews and explicitly approves the completed stage.

- [x] Create isolated package metadata, ignore rules, and a reproducible dependency lock.
- [x] Write and run failing tests for URL input validation, result provenance/status
  invariants, timezone normalization, and JSON round trips in `tests/unit/test_models.py`.
- [x] Implement `types.py` and `models.py` with Pydantic contracts and public exports.
- [x] Write and run failing tests for TOML loading, precedence, nested override merging,
  unknown-setting rejection and operational bounds in `tests/unit/test_config.py`.
- [x] Implement `ScraperConfig`, `ProjectConfig`, `load_config(path)` and
  `resolve_config(global_settings, competitor_overrides, cli_overrides)` in `config.py`.
- [x] Define async fetcher, sitemap discovery, extraction, result sink and scraper service
  Protocols in `interfaces.py`; use application-owned `FetchedPage` and result models.
- [x] Write and run failing SDK-boundary tests in `tests/unit/test_crawl4ai_adapter.py`.
- [x] Implement browser, run and seeding configuration factories in `crawl4ai_adapter.py`;
  verify actual installed SDK settings without launching a browser or contacting websites.
- [x] Document boundaries, approved policies, model semantics, setup and review examples;
  create a runnable example TOML fixture and a complete SDK result fixture for future mocks.
- [x] Run all foundation tests, Ruff, wheel build, and an installed-package/config import
  smoke check. Review generated JSON Schema and Git status; report results and stop.

Review: submit all Stage 1 files and test evidence to the user. After approval only, commit
as `feat: initialize standalone crawl4ai scraper framework`; discuss Stage 2 afterward.

Verification: 51 tests passed; Ruff lint/format checks passed; lock consistency, sdist/wheel
build and isolated wheel installation/import checks passed on Windows with Python 3.12.13.
User review is pending. No commit has been created.

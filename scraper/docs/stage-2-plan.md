# Stage 2 implementation plan

Goal: discover and prioritize competitor pages from a homepage under one auditable,
bounded BestFirst/BFS frontier. Preserve the Stage 1 contracts and existing user changes.

Stage 1 is committed as `c1cb7c4`. At the start, flattened package files and inconsistent
test imports caused four collection errors. These are fixed by mapping the unchanged flat
source directory to the installed package. The pre-existing untracked README is untouched.

## Approved decisions

- Keep files directly under `src/` and adapt packaging. Setuptools supports the mapping
  for editable installs and wheels; no package files were moved.
- Use bounded sitemap fetching/parsing with HTTPX and defusedxml. Retain Crawl4AI for
  relevance scoring, URL patterns and the Stage 3 browser integration. Protego replaces
  the standard-library robots parser after reproducing wildcard/precedence failures.

## Work and verification

- [x] Inspect the committed files and reproduce the baseline import failures.
- [x] Review the official Crawl4AI discovery docs and installed public API signatures.
- [x] Resolve the two user decisions above before dependent changes.
- [x] Restore baseline package imports/build behavior with the selected layout.
- [x] Add failing tests for normalization, exact-host scope, relevance scoring and filters.
- [x] Implement `discovery/urls.py` and `discovery/relevance.py` without network calls.
- [x] Add failing tests for a deduplicated URL registry and deterministic BestFirst/BFS
  ordering, including shallower rediscovery and failed-attempt budget consumption.
- [x] Implement `discovery/traversal.py` with one competitor frontier and explicit URL
  dispositions. Always collect links from the last allowed page; defer excess candidates.
- [x] Add controlled HTTP tests for robots/sitemap discovery, nested indexes, malformed
  XML, cycles, resource limits, robots failures and blocked redirect destinations.
- [x] Implement sitemap discovery under the selected design; reuse SDK features where
  their behavior matches approved requirements and document any necessary adaptation.
- [x] Add a discovery orchestrator consuming the Stage 1 `PageFetcher` contract. Use
  synthetic fetch results to verify homepage + sitemap + internal-link traversal together.
- [x] Test domain checks on initial URLs and HTTP redirect destinations; record relevant
  unapproved external links without scheduling their fetches.
- [x] Verify page/depth/discovery limits, deduplication, progress of shallower paths,
  cancellation/resource cleanup and deterministic priority under asynchronous completion.
- [x] Run the full suite, lint/format checks, lock validation, package build and an
  installed-package import check. Use offline fixtures; do not crawl live websites.
- [x] Update architecture/setup notes for the implemented discovery interface and report
  exact changes, test evidence and remaining stage boundaries for user review.

No Stage 2 commit before review and explicit approval. The requested commit message is
`feat: implement intelligent page discovery and traversal`. No Stage 3 implementation
or remote push is included.

Verification on Windows/Python 3.12.13: 135 tests passed; Ruff lint and format checks
passed; the dependency lock is current; sdist and wheel builds passed; a separate wheel
environment passed package compatibility, browser-free imports, schema and offline sitemap
checks. Renderer navigation gates and live-browser verification remain Stage 3/4 work,
as documented in `discovery.md`. User review and the Stage 2 commit are pending.

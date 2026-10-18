# Scraper architecture and approved policies

## Scope and status

The scraper is a separately installable package under `scraper/`. Source files remain
directly under `src/`, as requested during Stage 2. Setuptools maps that directory to
the public `scraper` package for both editable installs and wheels.
It collects competitor website content for downstream analysis. It does not implement
FastAPI, PostgreSQL, OpenAI analysis, a frontend, scheduling or change detection.

Stage 1 implements packaging, input/output contracts, validated settings, SDK configuration
factories and interfaces. Stage 2 adds bounded sitemap/robots HTTP discovery, URL policy,
BestFirst/BFS traversal and discovery orchestration over the `PageFetcher` contract.
Stage 3 connects browser fetching, content extraction, writers and the CLI. Stage 4 adds
bounded retries, independent capacity deadlines and integration
verification. Importing
models does not load the SDK. See `discovery.md` and `extraction-and-output.md` for the
implemented APIs, verification commands and current limitations.

## Runtime flow

1. Receive one or more `CompetitorInput` values and validate homepage URLs.
2. Resolve defaults, global settings, competitor overrides and explicit CLI overrides.
3. Fetch the homepage once, discover sitemaps, and collect internal/external links.
4. Normalize URLs and apply the shared domain, relevance, exclusion and deduplication policy.
5. Put allowed candidates into one per-competitor frontier: BestFirst by adaptive relevance,
   or BFS by depth. BestFirst now uses OpenAI Decisions plus structural diversity and
   exploration; the Crawl4AI URL-pattern filter remains an eligibility gate.
6. Reserve page budget before dispatch. Run bounded batches under global and per-domain
   concurrency controls. Process each fetch for both content and further link discovery.
7. Assess fetched content with Decisions outside browser capacity slots; feed novelty and
   source-linked excerpts into subsequent selection. Extract conservative Markdown and
   consume the assessment category without additional extraction requests.
8. Emit pages and finish with URL dispositions, counts and a reason for completion.

The frontier ranks currently known candidates. Concurrency means an already scheduled
batch cannot be reordered when a newly discovered URL scores higher. This is bounded
BestFirst traversal, not a guarantee of the globally most relevant 50 pages on a website.

## Why a shared frontier

Approved choice: own a small frontier and registry, while using the official Crawl4AI SDK
for rendering, links and URL-pattern filtering. OpenAI Decisions evaluates usefulness;
explicit structural mode remains API-free. During the original Stage 2 the user
approved bounded sitemap fetching/parsing with HTTPX and defusedxml, because the native
seeder's default recursion and redirects do not enforce the required resource/scope policies.
Protego handles robots matching, including longest-match precedence and wildcard rules.
Native deep-crawl strategies are useful but their one-root entry point and success-based
page limit do not directly provide our combined sitemap/link budget and audit registry.
We will not copy the SDK crawler or access its private queues/resume-state representation.
The bounded registry is scanned for the next best eligible URL instead of accumulating
stale heap entries on rediscovery. At the default 5,000 records and 50 attempts this keeps
selection small, deterministic and easy to inspect. BFS selects by depth and discovery order.

See [deep crawling](https://docs.crawl4ai.com/core/deep-crawling/),
[URL seeding](https://docs.crawl4ai.com/core/url-seeding/) and the
[official strategy source](https://github.com/unclecode/crawl4ai/blob/main/crawl4ai/deep_crawling/bff_strategy.py).
Configuration factories are checked against the installed, pinned Crawl4AI 0.9.5 SDK.

## Component ownership

| Component | Input and output | Responsibility |
| --- | --- | --- |
| Configuration | TOML / typed overrides -> resolved `ScraperConfig` | Validation and precedence |
| Sitemap discoverer | Homepage + settings -> `DiscoveryBatch` | Bounded sitemap candidates and warnings |
| URL policy / frontier | Candidates + fetched links -> ordered eligible URLs | Scope, normalization, scoring, deduplication, depth and budget |
| Page fetcher | URL + settings -> `FetchedPage` | One browser attempt, metadata, HTML, Markdown, links and page errors |
| Content extractor | `FetchedPage` + competitor + settings -> `ScrapedPage` | Cleaning, category assignment and source preservation |
| Scraper service | Competitor input(s) + settings -> result(s) | Composition, limits, retry orchestration and progress |
| Exporter | Completed competitor result -> Markdown files + `CrawlExportSummary` | URL-based content paths, concise index and summary-last publication |

Only the adapter knows SDK-specific result types. `FetchedPage` is transient and includes
HTML and links; exported `ScrapedPage` deliberately contains Markdown and metadata instead.
Fetcher implementations must support async context management and release resources on
normal completion, failure and cancellation. `crawl_many()` yields completed competitor
results; it does not block an application's event loop with a nested `asyncio.run()`.

## Approved crawl semantics

- Default maximum depth is 3 and maximum pages is 50, both configurable.
- Homepage is depth 0 and consumes a page slot. Each distinct attempted page consumes
  one slot, including failures. Retries do not consume another distinct-page slot;
  at most two retries per attempted URL are configured by default.
- Sitemap seeds enter at logical depth 1 with `depth_basis="sitemap_seed"`. This does
  not assert a verified link distance. Linked children add one depth level. A sitemap
  candidate is deferred when `max_depth=0`; the homepage is still eligible.
- Default scope is the homepage hostname and its apex/`www` counterpart. Other hosts,
  including other subdomains, require approval through an exact `allowed_domains` list.
  That list adds to the homepage scope. Redirect destinations must be checked too.
- Relevant external links are recorded; unapproved external pages are not traversed.
  External news coverage that is not linked from crawled pages is not discovered by a
  website-only crawl. A search/news-provider integration is outside this component.
- Decisions scores bounded link context and assesses fetched content; no extra probe request
  is made to obtain context. Structural mode is API-free. See [decisions.md](decisions.md).
  A fetched title cannot retroactively affect that page's original dispatch priority.
- Keep low-scoring navigational pages eligible by default so useful descendants can be
  found. Exclude clearly irrelevant patterns, unsupported schemes/assets and login pages.
- Normalize conservatively: resolve relative links, remove fragments/tracking parameters,
  normalize scheme/host/default ports and retain meaningful query parameters and path case.
  Do not assume different trailing-slash paths or canonical tags identify identical content.
  Exact normalization/scoring algorithms and tests belong to Stage 2.
- Retain observed candidates even if they cannot be crawled. Default discovery cap is
  5,000 unique records per competitor. A cap sets `discovery_truncated`; it is not a
  promise to enumerate every URL on the site. Sitemap parsing/request bounds must be
  enforced in Stage 2 as well as the number of returned candidates.

## Operational policies

Default settings allow 4 page tasks per discovery run and 1 page per domain at a time,
with a 1-2 second randomized inter-request delay. Stage 2 enforces these per-run limits.
The Stage 3 service coordinates the global limit across up to 2 competitors; Stage 2's
`DiscoveryCrawler.run()` processes one competitor. Constructing a run config alone does
not enforce limits. The service owns page retries; the bounded HTTP reader owns discovery
retries, each consuming its existing HTTP request budget. SDK retries stay disabled.
The service shares hostname pacing/cooldowns across browser and discovery requests.

Robots compliance is mandatory; `respect_robots_txt` cannot be set to false. Factories
enable the SDK check by default; the concrete guarded adapter disables the redundant
SDK lookup. Browser and application robots checks use the same explicit user agent.
Stage 2 validates robots behavior for sitemap requests, their redirects and page preflight.
The concrete browser fetcher checks document navigation and every redirect hop before
requesting it. It aborts redirect responses and separately navigates to each checked next
hop because ordinary browser routing can miss automatic redirects. Third-party rendering
resources are allowed; embedded documents and popups are blocked. See Stage 3 usage for
the exact policy and local Chromium verification.
Unavailable robots rules
caused by timeouts/server errors should defer the affected host with a warning rather
than silently proceeding. A missing robots file is distinct from a retrieval failure.

Use fresh page content (`CacheMode.DISABLED`). The bounded sitemap reader handles robots
directives, conventional roots, nested XML indexes and gzip. It never probes candidate pages.
Default bounds are 20 sitemap documents, 50 HTTP requests (including robots and redirect
hops), index depth 3, 2 MiB per response/decompressed sitemap and 5 redirects per request.
XML DTDs/entities are rejected. The pending sitemap queue is bounded; child-index references
take priority over speculative roots. Limits set truncation flags rather than implying full
coverage. HTTP clients close on normal exit, errors and cancellation. Common Crawl and
external search are not enabled. The Stage 1 SDK seeding-config factory is retained for
compatibility but is not used by the bounded reader. Tests confine SDK caches to temp paths.

Default navigation uses `domcontentloaded`, a 45-second active attempt deadline and a
10-second selector wait limit. Redirect render hops share the active deadline; capacity
and document pacing waits use a separate 120-second bound. The SDK navigation timer also
allows routing wait time, while the adapter enforces the active deadline. Optional scrolling is
limited to 5 steps. Per-site rules use URL globs, CSS waits and explicit load-more selectors
with finite click/scroll limits. Stage 3 selects the first matching rule and executes
explicit bounded load-more clicks before retrieving the final DOM.
Arbitrary buttons are not guessed. Page-specific failures are recorded and do not abort
other competitors; cancellation must propagate to release browser resources.
See [integration.md](integration.md) for retry classification, cleanup deadlines and
interruption guarantees. TLS verification is enabled for HTTP and browser requests.

## Result semantics and integration

`ScrapedPage` holds competitor identity, homepage, requested/final URLs, title, category,
UTC timestamp, fetch status, HTTP status, attempt count, full/filtered/cleaned Markdown,
JSON-compatible metadata and an error message on failure. A successful extracted page
must contain source Markdown. A failed page may retain useful partial content.

`DiscoveredUrl` keeps the observed URL and normalized identity separately, source, parent,
timestamp, depth/basis, relevance score, disposition and reason. One normalized registry
entry can accumulate additional discovery evidence in Stage 2 without duplicating crawl
work. `discovery_count` retains the total observations; at most 8 distinct evidence records
per URL bound provenance storage. Shallower paths update descendant depths without refetching
their parents. Skipped/deferred/external entries require a reason; they do not create pages.

`CompetitorCrawlResult` uses schema version `1.1`, timing, effective config, result status,
completion reason, page list, URL registry, truncation flag and warnings. Summary fields
are derived from its pages and registry; supplied mismatching counts are rejected.
`successful`/`failed` count page outcomes, `skipped`/`deferred`/`external`/`pending` count
registry dispositions, and `discovered` counts all unique registry records. These numbers
do not claim all sitemap or site URLs were enumerated. `pending` is available for an
interrupted run; normal completion must finalize eligible remaining URLs as deferred.

The CLI exports one directory per competitor as it completes: content-only `.md` files
and a schema `2.1` `CrawlExportSummary` index containing relative file references, counts,
timing and bounded discovery provenance. The exporter stages the files and publishes the
index last as a completion marker. It includes compact selection/usage diagnostics;
opt-in `decisions.jsonl` is published before that marker. Existing directories require a
fresh output root.
The previous JSON/JSONL file formats were replaced; historical generated data is retained.
Backend and LLM teams can read the index plus Markdown or await the unchanged
`CompetitorScraper` API directly. See [output-layout.md](output-layout.md).

## Delivery and Git gates

1. Foundation, model/configuration tests and SDK configuration checks.
2. Discovery, shared traversal, domain/relevance policy and fixture tests.
3. Extraction, dynamic rules, categories, JSON/JSONL and multiple-homepage CLI.
4. Reliability, resource cleanup, mock/integration tests and integration documentation.

Stop for review after every stage. Commit only after explicit approval, using the four
requested messages. Do not push without permission. Live competitor tests require the
user's approval in Stage 4. Default tests use fixtures without launching a browser.
Opt-in Stage 3 Chromium tests use loopback servers only.

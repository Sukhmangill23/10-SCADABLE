# Scraper architecture and approved policies

## Scope and status

The scraper is a separately installable package under `scraper/`, with a `src/` layout.
It collects competitor website content for downstream analysis. It does not implement
FastAPI, PostgreSQL, OpenAI analysis, a frontend, scheduling or change detection.

Stage 1 implements the foundation only: packaging, input/output contracts, validated
settings, SDK configuration factories and interfaces. Importing models does not load
the SDK. Interface methods are Protocol declarations, not runnable implementations.
No empty modules or fake crawl results represent unfinished stages.

## Runtime flow planned for Stages 2-4

1. Receive one or more `CompetitorInput` values and validate homepage URLs.
2. Resolve defaults, global settings, competitor overrides and explicit CLI overrides.
3. Fetch the homepage once, discover sitemaps, and collect internal/external links.
4. Normalize URLs and apply the shared domain, relevance, exclusion and deduplication policy.
5. Put allowed candidates into one per-competitor frontier: BestFirst by keyword relevance,
   or BFS by depth. Reuse the SDK keyword scorer and URL/domain filters where suitable.
6. Reserve page budget before dispatch. Run bounded batches under global and per-domain
   concurrency controls. Process each fetch for both content and further link discovery.
7. Extract conservative Markdown and categories from the existing fetch result without
   another request. Preserve full source Markdown and metadata even when filtering is used.
8. Emit pages and finish with URL dispositions, counts and a reason for completion.

The frontier ranks currently known candidates. Concurrency means an already scheduled
batch cannot be reordered when a newly discovered URL scores higher. This is bounded
BestFirst traversal, not a guarantee of the globally most relevant 50 pages on a website.

## Why a shared frontier

Approved choice: own a small queue and registry, while using the official Crawl4AI SDK
for rendering, links, sitemap seeding, scoring/filtering and dispatch where appropriate.
Native deep-crawl strategies are useful but their one-root entry point and success-based
page limit do not directly provide our combined sitemap/link budget and audit registry.
We will not copy the SDK crawler or access its private queues/resume-state representation.

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
| Result sink | Page and final competitor result -> local output | JSON/JSONL serialization, independent of crawling |

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
- Scoring uses configured category keywords in URLs, known link titles and fetched page
  titles. No extra page request is made just to learn a title, and no LLM classifies relevance.
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

Default settings allow 4 page tasks globally, 2 competitors concurrently and 1 page per
domain at a time, with a 1-2 second randomized inter-request delay. The service will own
these shared limits: constructing a run config does not enforce them. Retries need a
single owner to avoid multiplying SDK, dispatcher and service retry budgets.

Robots compliance is mandatory; `respect_robots_txt` cannot be set to false. Factories
enable the SDK check and give browser and robots checks the same explicit user agent.
Stage 2 must validate robots behavior for sitemap requests, navigation and redirects;
the factory alone does not establish end-to-end compliance. Unavailable robots rules
caused by timeouts/server errors should defer the affected host with a warning rather
than silently proceeding. A missing robots file is distinct from a retrieval failure.

Use fresh page content (`CacheMode.DISABLED`). Sitemap seeding uses `source="sitemap"`,
`force=True`, and no live checks/head extraction to avoid hidden candidate page fetches.
Its low-level nonsense filtering is disabled so application policy can record reasons.
Common Crawl and external search are not enabled. Seeder and browser storage paths must
be supplied by the runtime owner; tests confine SDK caches to temporary directories.

Default navigation uses `domcontentloaded`, a 45-second navigation timeout and a 10-second
selector wait limit. The service must also enforce a total attempt deadline around the
SDK call: a navigation timeout is not a total interaction timeout. Optional scrolling is
limited to 5 steps. Per-site rules use URL globs, CSS waits and explicit load-more selectors
with finite click/scroll limits. Rule selection and button execution are Stage 3 work.
Arbitrary buttons are not guessed. Page-specific failures are recorded and do not abort
other competitors; cancellation must propagate to release browser resources.

## Result semantics and integration

`ScrapedPage` holds competitor identity, homepage, requested/final URLs, title, category,
UTC timestamp, fetch status, HTTP status, attempt count, full/filtered/cleaned Markdown,
JSON-compatible metadata and an error message on failure. A successful extracted page
must contain source Markdown. A failed page may retain useful partial content.

`DiscoveredUrl` keeps the observed URL and normalized identity separately, source, parent,
timestamp, depth/basis, relevance score, disposition and reason. One normalized registry
entry can accumulate additional discovery evidence in Stage 2 without duplicating crawl
work. Skipped/deferred/external entries require a reason; they do not create fetched pages.

`CompetitorCrawlResult` uses schema version `1.0`, timing, effective config, result status,
completion reason, page list, URL registry, truncation flag and warnings. Summary fields
are derived from its pages and registry; supplied mismatching counts are rejected.
`successful`/`failed` count page outcomes, `skipped`/`deferred`/`external`/`pending` count
registry dispositions, and `discovered` counts all unique registry records. These numbers
do not claim all sitemap or site URLs were enumerated. `pending` is available for an
interrupted run; normal completion must finalize eligible remaining URLs as deferred.

Planned JSON contains complete competitor result objects in a versioned run document.
Planned JSONL contains typed `page` records and one `competitor_summary` record per
competitor, without repeating page bodies in the summary. Writers and run-document models
are finalized in Stage 3. Backend and LLM teams can import the contracts now and later
await the service directly; no API server or database is needed to consume the results.

## Delivery and Git gates

1. Foundation, model/configuration tests and SDK configuration checks.
2. Discovery, shared traversal, domain/relevance policy and fixture tests.
3. Extraction, dynamic rules, categories, JSON/JSONL and multiple-homepage CLI.
4. Reliability, resource cleanup, mock/integration tests and integration documentation.

Stop for review after every stage. Commit only after explicit approval, using the four
requested messages. Do not push without permission. Live competitor tests require the
user's approval in Stage 4. Current tests are offline and do not launch a browser.

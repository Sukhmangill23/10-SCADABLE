# Stage 2: discovery and traversal

Implemented under `src/discovery/`. Files remain directly under `src/`; setuptools maps
the directory to the installed `scraper` package. No source files were moved.

## Components

| Module | API | Responsibility |
| --- | --- | --- |
| `urls.py` | `normalize_url`, `DomainScope` | Conservative URL identities and exact approved hosts |
| `relevance.py` | `UrlPolicy` | URL eligibility, scope, extension and pattern exclusions |
| `evidence.py` | `link_observations`, `EvidenceLedger` | Bounded HTML context and source-linked feedback |
| `selection.py` | `AdaptiveSelection` | Decision cycles, content assessment and fallback |
| `traversal.py` | `UrlFrontier` | Deduplicated records, budgets, priorities, depth and dispositions |
| `http.py` | `GuardedHttpClient` | Explicit user agent, robots, redirect gates and bounded HTTP |
| `sitemaps.py` | `BoundedSitemapDiscoverer` | Sitemap roots, robots directives, indexes and gzip |
| `engine.py` | `DiscoveryCrawler`, `DiscoveryRun` | Homepage + sitemap + internal-link orchestration |

`DiscoveryRun` retains fetched pages for Stage 3 extraction. No second fetch is required.
It reports attempted pages, effective settings, URL records, warnings, truncation and the
completion reason. It supports Pydantic JSON round trips but does not write output files.

## API composition

```python
from scraper import CompetitorInput, ScraperConfig, resolve_config
from scraper.discovery.engine import DiscoveryCrawler
from scraper.discovery.http import GuardedHttpClient
from scraper.discovery.sitemaps import BoundedSitemapDiscoverer


async def discover_competitor(fetcher, competitor: CompetitorInput, global_settings: ScraperConfig):
    effective = resolve_config(global_settings, competitor.overrides)
    async with GuardedHttpClient(str(competitor.homepage_url), effective) as guard:
        crawler = DiscoveryCrawler(fetcher, BoundedSitemapDiscoverer(), robots_guard=guard)
        return await crawler.run(competitor, global_settings)
```

The supplied fetcher must implement `PageFetcher`'s async context manager and `fetch()`.
It must enforce domain and robots policy before every browser navigation and redirect hop.
Stage 2 rejects an unexpected unapproved final URL and does not expand its content, but
that check cannot prevent a bad fetcher from having already requested the destination.
The concrete Crawl4AI browser adapter, extraction and CLI are implemented in Stage 3; see
[extraction and output](extraction-and-output.md). Stage 2 itself tests rendering through
controlled fixtures and does not claim live-browser verification.
The HTTP sitemap/robots implementation is concrete and independently reusable.

`robots_guard.check(url)` returns the minimum interval from robots rules or raises
`RequestBlocked`. A robots refusal releases a page reservation and creates a skipped or
deferred URL record; it does not pretend that page content was fetched.

## Policy details

- Homepage is fetched first at depth 0. Sitemap seeds have logical depth 1 and a
  `sitemap_seed` depth basis; this does not assert a known internal-link distance.
- BestFirst uses Decisions relevance, section diversity, and observed content novelty,
  with a configurable exploration fraction (20% by default). BFS orders by depth and
  discovery order and skips candidate-scoring calls. Fetch batches stop at scoring
  checkpoints; already-dispatched work is not reordered.
- Keyword scoring and thresholds have been removed. The default LLM mode requires
  `OPENAI_API_KEY`; `selection.mode="structural"` is API-free. Rendered HTML supplies
  bounded anchor/heading/nearby-text context without probe requests. See
  [Decisions](decisions.md) for caching, budgets, feedback, and migration details.
- Normalize relative references, scheme/host/default ports, fragments and known tracking
  parameters. Preserve meaningful query bytes/order, repeated keys, path case and trailing
  slash distinctions. Requested/observed source URLs remain available in the registry.
- Exact homepage/apex-www hosts and explicitly approved extra hosts are eligible. An
  approved host does not approve its subdomains. Otherwise eligible external links are
  recorded without being scored or scheduled; asset/login exclusions receive skipped reasons.
- Distinct page attempts consume the budget, including failures. Service retries reuse
  that reservation. Standalone `DiscoveryCrawler` remains a single-attempt orchestrator.
  Robots refusals occur before fetching and do not consume a page slot.
- Every successful boundary page still contributes links after the page limit is reached.
  Additional candidates are recorded as deferred, up to the independent discovery cap.
- Repeated normalized URLs accumulate an observation count and up to 8 distinct evidence
  records. A shorter path can reopen a depth-limited candidate and relax descendants
  without fetching their parent again.
- Concurrency is limited per discovery run and per hostname. Delays respect the configured
  interval and robots Crawl-delay/Request-rate. Cancellation propagates and closes the
  fetcher; expected page/network failures are retained while other candidates continue.

## Sitemap and robots bounds

Defaults: 20 sitemap documents, 50 HTTP requests, sitemap-index depth 3, 2 MiB per response
and decompressed sitemap, 5 redirects, and 30 seconds for total sitemap discovery. Index
children take priority over speculative root fallbacks. Cycles and duplicate documents
are prevented; XML DTD/entity content is rejected. No candidate HTML, Common Crawl or
third-party discovery service is fetched by this component.

Robots are parsed by Protego, independently of directive ordering, with wildcard and
longest-match handling. Rules are cached per origin for the client session. Missing
robots files (404/410) allow requests; access refusals and server/network errors do not
silently grant permission. Sitemap redirects are checked at every hop before requesting
the next destination. Unapproved external sitemap hosts are reported, not followed.

HTTPX and defusedxml were already SDK dependencies and are now declared directly because
our code imports them. Protego is a small additional parser dependency. Crawl4AI remains
pinned at 0.9.5; its public pattern filter is used rather than copied. Lxml is declared
directly for local HTML context parsing; its already-locked version is retained.
Setuptools supports the requested flat source directory in both editable and wheel builds.

## Offline review

From `scraper/`:

```powershell
uv sync --locked
uv run --locked pytest -q
uv run --locked pytest tests/integration/test_discovery_workflow.py -v
uv run --locked ruff check .
uv run --locked ruff format --check .
uv build
```

The integration test uses the real frontier, sitemap reader, robots client and orchestrator;
only HTTP and rendering are replaced with synthetic fixtures. Tests cover both traversal
strategies, source preservation, deduplication, shorter paths, page/depth/discovery limits,
external hosts, robots failures, redirects, XML/gzip bounds, concurrency and cancellation.
No browser or live competitor website is contacted by these default checks. Live testing
requires explicit approval. The original discovery stage was committed as `1d8e50e`;
the OpenAI-guided discovery update was committed as `f97af15`. Its subsequent export and
documentation stage is awaiting review; see [decision-validation.md](decision-validation.md).
See [integration.md](integration.md) for the service retry and shared pacing policy.

References: [Crawl4AI deep crawling](https://docs.crawl4ai.com/core/deep-crawling/),
[HTTPX transports](https://www.python-httpx.org/advanced/transports/),
[defusedxml](https://github.com/tiran/defusedxml), and
[Protego](https://github.com/scrapy/protego).

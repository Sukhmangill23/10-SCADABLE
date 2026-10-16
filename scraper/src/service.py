"""Async, backend-independent composition of discovery, rendering and extraction."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable, Sequence

import httpx

from .config import CompetitorInput, ScraperConfig, resolve_config
from .discovery.engine import DiscoveryCrawler
from .discovery.http import GuardedHttpClient
from .discovery.sitemaps import BoundedSitemapDiscoverer
from .discovery.urls import normalize_url
from .extraction import MarkdownExtractor
from .interfaces import ContentExtractor, PageFetcher, RobotsGuard
from .limits import HostLimiter
from .models import CompetitorCrawlResult
from .types import UrlDisposition, utc_now

logger = logging.getLogger(__name__)
FetcherFactory = Callable[[CompetitorInput, ScraperConfig, RobotsGuard], PageFetcher]


def _browser_factory(competitor, settings, guard, host_limiter):
    from .browser import Crawl4AIFetcher

    return Crawl4AIFetcher(str(competitor.homepage_url), settings, guard, host_limiter=host_limiter)


class _Capacity:
    def __init__(self, settings: ScraperConfig):
        self.pages = asyncio.Semaphore(settings.max_concurrency)
        self.hosts = HostLimiter(settings.per_domain_concurrency)


class _LimitedFetcher:
    def __init__(
        self,
        fetcher: PageFetcher,
        capacity: _Capacity,
        guard: RobotsGuard,
        *,
        limit_source_host: bool,
    ):
        self.fetcher = fetcher
        self.capacity = capacity
        self.guard = guard
        self.limit_source_host = limit_source_host

    async def __aenter__(self):
        self.active = await self.fetcher.__aenter__()
        return self

    async def __aexit__(self, *exc):
        await self.fetcher.__aexit__(*exc)

    async def fetch(self, url, settings):
        async with self.capacity.pages:
            logger.info("Fetching %s", url)
            if self.limit_source_host:
                # An injected fetcher owns any redirect handling. The default browser
                # adapter holds shared slots for each actual navigation hostname.
                async with self.capacity.hosts.slot(str(url)):
                    minimum = await self.guard.check(str(url))
                    await self.capacity.hosts.pace(str(url), settings, minimum)
                    page = await self.active.fetch(url, settings)
            else:
                page = await self.active.fetch(url, settings)
            logger.info("Fetched %s: %s", url, page.crawl_status)
            return page


class CompetitorScraper:
    def __init__(
        self,
        *,
        fetcher_factory: FetcherFactory | None = None,
        extractor: ContentExtractor | None = None,
        http_transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._fetcher_factory = fetcher_factory
        self._extractor = extractor or MarkdownExtractor()
        self._transport = http_transport

    async def crawl(
        self,
        competitor: CompetitorInput,
        settings: ScraperConfig | None = None,
        *,
        cli_overrides: ScraperConfig | None = None,
    ) -> CompetitorCrawlResult:
        effective = resolve_config(settings, competitor.overrides, cli_overrides)
        return await self._crawl(competitor, settings, cli_overrides, _Capacity(effective))

    async def _crawl(self, competitor, global_settings, cli_overrides, capacity):
        settings = resolve_config(global_settings, competitor.overrides, cli_overrides)
        started = utc_now()
        logger.info("Starting %s", competitor.homepage_url)
        try:
            async with GuardedHttpClient(
                str(competitor.homepage_url), settings, transport=self._transport
            ) as guard:
                custom = self._fetcher_factory is not None
                owned = (
                    self._fetcher_factory(competitor, settings, guard)
                    if custom
                    else _browser_factory(competitor, settings, guard, capacity.hosts)
                )
                fetcher = _LimitedFetcher(owned, capacity, guard, limit_source_host=custom)
                discovery = await DiscoveryCrawler(
                    fetcher, BoundedSitemapDiscoverer(transport=self._transport), robots_guard=guard
                ).run(competitor, global_settings, cli_overrides=cli_overrides)
            pages = [
                self._extractor.extract(page, competitor, settings)
                for page in discovery.fetched_pages
            ]
            failures = {
                normalize_url(str(page.source_url)).normalized: page.error_message
                for page in pages
                if page.crawl_status == "failed"
            }
            records = [
                record.model_copy(
                    update={
                        "disposition": UrlDisposition.FAILED,
                        "reason": failures[str(record.normalized_url)],
                    }
                )
                if str(record.normalized_url) in failures
                else record
                for record in discovery.discovered_urls
            ]
            successes = sum(page.crawl_status == "success" for page in pages)
            policy_failures = any(
                record.reason
                and record.reason.startswith("robots_")
                and record.disposition == UrlDisposition.DEFERRED
                for record in records
            )
            status = (
                "failed"
                if not successes
                else ("partial" if failures or policy_failures else "success")
            )
            result = CompetitorCrawlResult(
                competitor_name=competitor.display_name,
                homepage_url=competitor.homepage_url,
                started_at=discovery.started_at,
                finished_at=utc_now(),
                run_status=status,
                completion_reason=discovery.completion_reason,
                effective_config=settings,
                pages=pages,
                discovered_urls=records,
                discovery_truncated=discovery.discovery_truncated,
                warnings=discovery.warnings,
            )
        except Exception as error:
            # Isolate competitor infrastructure failures, while cancellation propagates.
            logger.exception("Competitor failed: %s", competitor.homepage_url)
            result = CompetitorCrawlResult(
                competitor_name=competitor.display_name,
                homepage_url=competitor.homepage_url,
                started_at=started,
                finished_at=utc_now(),
                run_status="failed",
                completion_reason="failed",
                effective_config=settings,
                warnings=[f"{type(error).__name__}: {error}"],
            )
        logger.info(
            "Finished %s: %s (%d successful, %d failed)",
            competitor.homepage_url,
            result.run_status,
            result.summary.successful,
            result.summary.failed,
        )
        return result

    async def crawl_many(
        self,
        competitors: Sequence[CompetitorInput],
        global_settings: ScraperConfig | None = None,
        *,
        cli_overrides: ScraperConfig | None = None,
    ) -> AsyncIterator[CompetitorCrawlResult]:
        """Yield completed results; closing this iterator cancels and cleans up workers.

        Global/CLI concurrency settings are ceilings across the run. A competitor may
        lower its own discovery parallelism, but cannot increase those shared ceilings.
        """
        limits = resolve_config(global_settings, cli_overrides=cli_overrides)
        # Invalid combinations must fail before workers are created, rather than leave
        # a consumer waiting on a queue after a worker dies during config resolution.
        for competitor in competitors:
            resolve_config(global_settings, competitor.overrides, cli_overrides)
        capacity = _Capacity(limits)
        count = min(len(competitors), limits.max_concurrent_competitors)
        pending = iter(competitors)
        results: asyncio.Queue[CompetitorCrawlResult] = asyncio.Queue(maxsize=max(1, count))

        async def worker():
            for competitor in pending:
                result = await self._crawl(competitor, global_settings, cli_overrides, capacity)
                await results.put(result)

        workers = [asyncio.create_task(worker()) for _ in range(count)]
        try:
            for _ in competitors:
                yield await results.get()
        finally:
            for task in workers:
                task.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

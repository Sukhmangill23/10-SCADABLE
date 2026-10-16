"""Incremental homepage/sitemap/link discovery over an injected, policy-aware fetcher.

This stage returns reusable FetchedPage objects. Cleaning, categories, output writers and
the concrete SDK browser adapter are Stage 3 work; no second content fetch is necessary.
"""

import asyncio
import random
from collections import Counter
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field

from ..config import CompetitorInput, ScraperConfig, resolve_config
from ..interfaces import PageFetcher, RobotsGuard, SitemapDiscoverer
from ..models import DiscoveredUrl, FetchedPage
from ..types import ContractModel, UtcTimestamp, utc_now
from .http import RequestBlocked
from .traversal import UrlFrontier


class DiscoveryRun(ContractModel):
    competitor: CompetitorInput
    effective_config: ScraperConfig
    started_at: UtcTimestamp
    finished_at: UtcTimestamp
    fetched_pages: list[FetchedPage] = Field(default_factory=list)
    discovered_urls: list[DiscoveredUrl] = Field(default_factory=list)
    attempted_pages: int
    discovery_truncated: bool
    completion_reason: Literal["completed", "page_limit", "discovery_limit"]
    warnings: list[str] = Field(default_factory=list)


class DiscoveryCrawler:
    def __init__(
        self, fetcher: PageFetcher, sitemaps: SitemapDiscoverer, *, robots_guard: RobotsGuard
    ):
        self._fetcher = fetcher
        self._sitemaps = sitemaps
        self._robots = robots_guard

    async def run(
        self,
        competitor: CompetitorInput,
        global_settings: ScraperConfig | None = None,
        *,
        cli_overrides: ScraperConfig | None = None,
    ) -> DiscoveryRun:
        settings = resolve_config(global_settings, competitor.overrides, cli_overrides)
        started = utc_now()
        frontier = UrlFrontier(str(competitor.homepage_url), settings)
        pages: list[FetchedPage] = []
        warnings: list[str] = []
        pace_locks: dict[str, asyncio.Lock] = {}

        async def attempt(record):
            url = str(record.normalized_url)
            try:
                async with asyncio.timeout(settings.discovery_timeout_seconds):
                    robots_delay = await self._robots.check(url)
            except TimeoutError:
                return RequestBlocked("robots_unavailable", url)
            except RequestBlocked as error:
                return error
            host = urlsplit(url).hostname
            async with pace_locks.setdefault(host, asyncio.Lock()):
                interval = max(random.uniform(*settings.request_delay_seconds), robots_delay)
                if interval > 0:
                    await asyncio.sleep(interval)
            try:
                async with asyncio.timeout(settings.page_timeout_seconds):
                    return await fetcher.fetch(record.normalized_url, settings)
            except (TimeoutError, OSError) as error:
                return FetchedPage(
                    source_url=url,
                    crawl_timestamp=utc_now(),
                    crawl_status="failed",
                    error_message=f"{type(error).__name__}: {error}",
                )

        async def seed_sitemaps():
            try:
                async with asyncio.timeout(settings.discovery_timeout_seconds):
                    batch = await self._sitemaps.discover(competitor.homepage_url, settings)
                warnings.extend(batch.warnings)
                frontier.truncated |= batch.truncated
                for record in batch.urls:
                    frontier.discover(
                        str(record.url),
                        parent_url=str(record.parent_url) if record.parent_url else None,
                        depth=1,
                        source="sitemap",
                        depth_basis="sitemap_seed",
                    )
            except (TimeoutError, OSError) as error:
                warnings.append(f"sitemap_discovery_failed: {type(error).__name__}: {error}")

        seeded = False
        async with self._fetcher as fetcher:
            while True:
                hosts = Counter()
                batch = []
                while len(batch) < settings.max_concurrency:
                    record = frontier.pop_next(
                        eligible=lambda item, counts=hosts: (
                            counts[urlsplit(str(item.normalized_url)).hostname]
                            < settings.per_domain_concurrency
                        )
                    )
                    if record is None:
                        break
                    batch.append(record)
                    hosts[urlsplit(str(record.normalized_url)).hostname] += 1
                if not batch:
                    break
                async with asyncio.TaskGroup() as group:
                    tasks = [group.create_task(attempt(record)) for record in batch]
                # Process in dispatch order so network completion timing cannot reorder
                # discovery evidence or priorities for the next batch.
                for record, task in zip(batch, tasks, strict=True):
                    outcome = task.result()
                    url = str(record.normalized_url)
                    if isinstance(outcome, RequestBlocked):
                        frontier.reject_reserved(
                            url,
                            reason=outcome.reason,
                            deferred=outcome.reason != "robots_disallowed",
                        )
                        warnings.append(str(outcome))
                        continue
                    if outcome.final_url and not frontier.policy.scope.allows(
                        str(outcome.final_url)
                    ):
                        frontier.discover(
                            str(outcome.final_url),
                            parent_url=url,
                            depth=record.depth,
                            title=outcome.page_title or "",
                            source="external_link",
                        )
                        outcome = FetchedPage(
                            source_url=url,
                            final_url=outcome.final_url,
                            crawl_timestamp=outcome.crawl_timestamp,
                            crawl_status="failed",
                            error_message="domain_not_approved_redirect",
                        )
                    success = outcome.crawl_status == "success"
                    frontier.complete(url, success=success, error=outcome.error_message)
                    if outcome.page_title:
                        frontier.note_title(url, outcome.page_title)
                    pages.append(outcome)
                    if success:
                        depth = frontier.get(url).depth + 1
                        for link in outcome.links:
                            source = (
                                "internal_link"
                                if frontier.policy.scope.allows(str(link.url))
                                else "external_link"
                            )
                            frontier.discover(
                                str(link.url),
                                parent_url=url,
                                depth=depth,
                                source=source,
                                title=link.title or link.text,
                            )
                if not seeded:
                    await seed_sitemaps()
                    seeded = True
        frontier.finalize()
        if frontier.invalid_links:
            warnings.append(f"invalid_links_ignored: {frontier.invalid_links}")
        records = frontier.records
        reason = (
            "page_limit"
            if any(item.reason == "page_limit" for item in records)
            else ("discovery_limit" if frontier.truncated else "completed")
        )
        return DiscoveryRun(
            competitor=competitor,
            effective_config=settings,
            started_at=started,
            finished_at=utc_now(),
            fetched_pages=pages,
            discovered_urls=records,
            attempted_pages=frontier.attempted_pages,
            discovery_truncated=frontier.truncated,
            completion_reason=reason,
            warnings=list(dict.fromkeys(warnings)),
        )

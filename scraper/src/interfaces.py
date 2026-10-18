"""Component boundaries for Stages 2-4, expressed without SDK-specific types.

These Protocols are contracts, not a partially working crawl service. Resource-owning
implementations must close their clients/browsers on normal exit, errors and cancellation.
"""

from collections.abc import AsyncIterator, Sequence
from types import TracebackType
from typing import Protocol, Self

from pydantic import Field

from .config import CompetitorInput, ScraperConfig
from .decision_models import (
    CandidateScore,
    CollectedExcerpt,
    DecisionCandidate,
    DecisionTraceRecord,
    DecisionUsageSummary,
    PageAssessment,
)
from .models import CompetitorCrawlResult, DiscoveredUrl, FetchedPage, ScrapedPage
from .types import ContractModel, NonEmptyText, WebUrl


class DiscoveryBatch(ContractModel):
    urls: list[DiscoveredUrl] = Field(default_factory=list)
    truncated: bool = False
    warnings: list[NonEmptyText] = Field(default_factory=list)


class DecisionProvider(Protocol):
    """One competitor's selection evaluator; the service owns its lifetime/capacity."""

    async def __aenter__(self) -> Self: ...

    async def __aexit__(self, *exc) -> None: ...

    async def score_candidates(
        self, candidates: Sequence[DecisionCandidate]
    ) -> list[CandidateScore]: ...

    async def assess_content(
        self, page: FetchedPage, ledger: Sequence[CollectedExcerpt] = ()
    ) -> PageAssessment: ...

    @property
    def summary(self) -> DecisionUsageSummary: ...

    @property
    def trace_records(self) -> list[DecisionTraceRecord]: ...


class PageFetcher(Protocol):
    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def fetch(self, url: WebUrl, settings: ScraperConfig) -> FetchedPage:
        """One attempt; failures become outcomes and cancellation propagates.

        Implementations must enforce domain and robots policy before every navigation,
        including redirect hops. A final-URL check after fetching cannot prevent egress.
        """
        ...


class RobotsGuard(Protocol):
    async def check(self, url: str) -> float:
        """Return the minimum request interval or raise discovery.http.RequestBlocked."""
        ...


class SitemapDiscoverer(Protocol):
    async def discover(self, homepage: WebUrl, settings: ScraperConfig) -> DiscoveryBatch:
        """Return bounded sitemap candidates; close HTTP clients before returning."""
        ...


class ContentExtractor(Protocol):
    def extract(
        self, page: FetchedPage, competitor: CompetitorInput, settings: ScraperConfig
    ) -> ScrapedPage:
        """Clean/categorize an existing fetch result without additional network requests."""
        ...


class ScraperService(Protocol):
    async def crawl(
        self, competitor: CompetitorInput, settings: ScraperConfig
    ) -> CompetitorCrawlResult: ...

    def crawl_many(
        self, competitors: Sequence[CompetitorInput], global_settings: ScraperConfig
    ) -> AsyncIterator[CompetitorCrawlResult]:
        """Yield completed competitor results; resolve each competitor's overrides separately."""
        ...

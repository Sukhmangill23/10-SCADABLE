"""Application-owned input, fetch and output contracts; no SDK or backend imports."""

from typing import Annotated, Literal, Self

from pydantic import Field, JsonValue, model_validator

from .config import CompetitorInput, NonNegativeInt, PositiveInt, ScraperConfig
from .types import (
    ContractModel,
    CrawlStatus,
    DiscoverySource,
    HomepageUrl,
    NonEmptyText,
    PageCategory,
    UrlDisposition,
    UtcTimestamp,
    WebUrl,
    utc_now,
)

__all__ = [
    "CompetitorInput",
    "CompetitorCrawlResult",
    "CrawlSummary",
    "DiscoveredLink",
    "DiscoveredUrl",
    "FetchedPage",
    "ScrapedPage",
]


class DiscoveredLink(ContractModel):
    url: WebUrl
    text: str = ""
    title: str | None = None


class DiscoveredUrl(ContractModel):
    url: WebUrl
    normalized_url: WebUrl
    discovery_source: DiscoverySource
    discovered_at: UtcTimestamp = Field(default_factory=utc_now)
    parent_url: WebUrl | None = None
    depth: NonNegativeInt | None = None
    depth_basis: Literal["homepage", "link", "sitemap_seed"] = "link"
    relevance_score: Annotated[float, Field(ge=0, le=1)] = 0.0
    disposition: UrlDisposition = UrlDisposition.PENDING
    reason: NonEmptyText | None = None

    @model_validator(mode="after")
    def explain_uncrawled_urls(self) -> Self:
        if (
            self.disposition
            in {
                UrlDisposition.SKIPPED,
                UrlDisposition.DEFERRED,
                UrlDisposition.EXTERNAL,
            }
            and self.reason is None
        ):
            raise ValueError("Skipped, deferred and external URLs require a reason")
        return self


class PageContent(ContractModel):
    source_url: WebUrl
    final_url: WebUrl | None = None
    page_title: str | None = None
    crawl_timestamp: UtcTimestamp
    crawl_status: CrawlStatus
    http_status: Annotated[int, Field(strict=True, ge=100, le=599)] | None = None
    attempt_count: PositiveInt = 1
    raw_markdown: str = ""
    filtered_markdown: str | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    error_message: NonEmptyText | None = None

    @model_validator(mode="after")
    def consistent_outcome(self) -> Self:
        if self.crawl_status == CrawlStatus.FAILED and self.error_message is None:
            raise ValueError("Failed pages require an error message")
        if self.crawl_status == CrawlStatus.SUCCESS:
            if self.error_message is not None:
                raise ValueError("Successful pages cannot have an error message")
            if self.http_status is not None and self.http_status >= 400:
                raise ValueError("HTTP error responses cannot be successful pages")
        return self


class FetchedPage(PageContent):
    """Transient boundary object; HTML is not included in exported ScrapedPage."""

    raw_html: str = ""
    links: list[DiscoveredLink] = Field(default_factory=list)


class ScrapedPage(PageContent):
    competitor_name: NonEmptyText
    homepage_url: HomepageUrl
    page_category: PageCategory = PageCategory.OTHER
    cleaned_markdown: str = ""

    @model_validator(mode="after")
    def successful_pages_have_content(self) -> Self:
        if self.crawl_status == CrawlStatus.SUCCESS and not self.raw_markdown.strip():
            raise ValueError("Successful extracted pages require source Markdown")
        return self


class CrawlSummary(ContractModel):
    successful: NonNegativeInt = 0
    failed: NonNegativeInt = 0
    skipped: NonNegativeInt = 0
    discovered: NonNegativeInt = 0
    deferred: NonNegativeInt = 0
    external: NonNegativeInt = 0
    pending: NonNegativeInt = 0


class CompetitorCrawlResult(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    competitor_name: NonEmptyText
    homepage_url: HomepageUrl
    started_at: UtcTimestamp
    finished_at: UtcTimestamp
    run_status: Literal["success", "partial", "failed", "cancelled"]
    completion_reason: Literal["completed", "page_limit", "discovery_limit", "cancelled", "failed"]
    effective_config: ScraperConfig = Field(default_factory=ScraperConfig)
    pages: list[ScrapedPage] = Field(default_factory=list)
    discovered_urls: list[DiscoveredUrl] = Field(default_factory=list)
    discovery_truncated: bool = False
    warnings: list[NonEmptyText] = Field(default_factory=list)
    summary: CrawlSummary = Field(default_factory=CrawlSummary)

    @model_validator(mode="after")
    def validate_result_and_derive_summary(self) -> Self:
        if self.finished_at < self.started_at:
            raise ValueError("finished_at must not precede started_at")
        if any(page.homepage_url != self.homepage_url for page in self.pages):
            raise ValueError("All pages must belong to this competitor homepage")
        urls = [str(record.normalized_url) for record in self.discovered_urls]
        if len(urls) != len(set(urls)):
            raise ValueError("Discovered URLs must have unique normalized URLs")
        summary = CrawlSummary(
            successful=sum(page.crawl_status == CrawlStatus.SUCCESS for page in self.pages),
            failed=sum(page.crawl_status == CrawlStatus.FAILED for page in self.pages),
            skipped=sum(url.disposition == UrlDisposition.SKIPPED for url in self.discovered_urls),
            discovered=len(self.discovered_urls),
            deferred=sum(
                url.disposition == UrlDisposition.DEFERRED for url in self.discovered_urls
            ),
            external=sum(
                url.disposition == UrlDisposition.EXTERNAL for url in self.discovered_urls
            ),
            pending=sum(url.disposition == UrlDisposition.PENDING for url in self.discovered_urls),
        )
        if "summary" in self.model_fields_set and self.summary != summary:
            raise ValueError("Summary counts do not match the page and URL records")
        object.__setattr__(self, "summary", summary)
        return self

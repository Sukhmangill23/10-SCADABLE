"""Public foundation API. Importing this package never starts a crawler."""

from .config import (
    CompetitorInput,
    DynamicRule,
    DynamicSettings,
    ProjectConfig,
    ScraperConfig,
    load_config,
    resolve_config,
)
from .models import (
    CompetitorCrawlResult,
    CrawlExportSummary,
    DiscoveredUrl,
    ExportedPage,
    FetchedPage,
    ScrapedPage,
)
from .types import CrawlStatus, DiscoverySource, PageCategory, UrlDisposition

__all__ = [
    "CompetitorCrawlResult",
    "CompetitorInput",
    "CrawlStatus",
    "CrawlExportSummary",
    "ExportedPage",
    "DiscoveredUrl",
    "DiscoverySource",
    "DynamicRule",
    "DynamicSettings",
    "FetchedPage",
    "PageCategory",
    "ProjectConfig",
    "ScrapedPage",
    "ScraperConfig",
    "UrlDisposition",
    "load_config",
    "resolve_config",
]

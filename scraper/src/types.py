"""Small shared types; importing these never imports or starts Crawl4AI."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    HttpUrl,
    StringConstraints,
)


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def _without_credentials(url: HttpUrl) -> HttpUrl:
    if url.username is not None or url.password is not None:
        raise ValueError("URLs must not contain credentials")
    return url


def _homepage_only(url: HttpUrl) -> HttpUrl:
    if url.path not in (None, "", "/") or url.query is not None or url.fragment is not None:
        raise ValueError("Provide a homepage URL without a subpage, query or fragment")
    return url


WebUrl = Annotated[HttpUrl, AfterValidator(_without_credentials)]
HomepageUrl = Annotated[WebUrl, AfterValidator(_homepage_only)]
UtcTimestamp = Annotated[AwareDatetime, AfterValidator(lambda value: value.astimezone(UTC))]


class PageCategory(StrEnum):
    POSITIONING = "positioning"
    PRICING = "pricing"
    PRODUCTS = "products"
    SERVICES = "services"
    FEATURES = "features"
    INTEGRATIONS = "integrations"
    CAREERS = "careers"
    HIRING = "hiring"
    NEWS = "news"
    BLOG = "blog"
    PRESS_RELEASE = "press_release"
    OTHER = "other"


class CrawlStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"


class DiscoverySource(StrEnum):
    HOMEPAGE = "homepage"
    SITEMAP = "sitemap"
    INTERNAL_LINK = "internal_link"
    EXTERNAL_LINK = "external_link"
    PAGINATION = "pagination"


class UrlDisposition(StrEnum):
    PENDING = "pending"
    CRAWLED = "crawled"
    FAILED = "failed"
    SKIPPED = "skipped"
    DEFERRED = "deferred"
    EXTERNAL = "external"


def utc_now() -> datetime:
    return datetime.now(UTC)

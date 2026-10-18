"""URL eligibility only; page usefulness is evaluated separately by Decisions."""

from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

from ..config import ScraperConfig
from ..types import UrlDisposition
from .urls import DomainScope

UNSUPPORTED_EXTENSIONS = frozenset(
    {
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".svg",
        ".webp",
        ".ico",
        ".mp4",
        ".mp3",
        ".woff",
        ".woff2",
        ".ttf",
        ".zip",
        ".gz",
        ".css",
        ".js",
        ".json",
        ".xml",
        ".txt",
    }
)


@dataclass(frozen=True)
class UrlDecision:
    disposition: UrlDisposition
    reason: str | None


class UrlPolicy:
    def __init__(self, homepage: str, settings: ScraperConfig):
        from crawl4ai.deep_crawling.filters import URLPatternFilter

        self.scope = DomainScope(homepage, settings)
        self.settings = settings
        self._exclude = URLPatternFilter(patterns=settings.excluded_url_patterns)

    def evaluate(self, url: str, *, homepage: bool = False) -> UrlDecision:
        path = unquote(urlsplit(url).path).lower()
        if PurePosixPath(path).suffix in UNSUPPORTED_EXTENSIONS:
            return UrlDecision(UrlDisposition.SKIPPED, "unsupported_extension")
        if not homepage and self._exclude.apply(url.lower()):
            return UrlDecision(UrlDisposition.SKIPPED, "excluded_pattern")
        if not self.scope.allows(url):
            return UrlDecision(UrlDisposition.EXTERNAL, "domain_not_approved")
        return UrlDecision(UrlDisposition.PENDING, None)

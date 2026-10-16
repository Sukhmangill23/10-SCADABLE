"""Deterministic keyword policy using the official Crawl4AI scorer and pattern filter."""

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
    score: float


class UrlPolicy:
    def __init__(self, homepage: str, settings: ScraperConfig):
        from crawl4ai.deep_crawling.filters import URLPatternFilter
        from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer

        self.scope = DomainScope(homepage, settings)
        self.settings = settings
        self._exclude = URLPatternFilter(patterns=settings.excluded_url_patterns)
        self._scorers = [
            KeywordRelevanceScorer(keywords=list(dict.fromkeys(word.lower() for word in words)))
            for words in settings.category_keywords.values()
            if words
        ]

    def score(self, url: str, title: str = "") -> float:
        """Use the strongest category match; domain names are not relevance evidence.

        Title evidence can promote an opaque URL without requiring a probe request.
        URL evidence is never diluted solely because no link title was available.
        """
        parts = urlsplit(url)
        path_query = unquote(parts.path + (f"?{parts.query}" if parts.query else ""))
        url_score = max((scorer.score(path_query) for scorer in self._scorers), default=0.0)
        title_score = max((scorer.score(title) for scorer in self._scorers), default=0.0)
        total = self.settings.url_keyword_weight + self.settings.title_keyword_weight
        if not title:
            return url_score if self.settings.url_keyword_weight > 0 else 0.0
        combined = (
            self.settings.url_keyword_weight * url_score
            + self.settings.title_keyword_weight * title_score
        ) / total
        return min(1.0, combined)

    def evaluate(self, url: str, *, title: str = "", homepage: bool = False) -> UrlDecision:
        score = self.score(url, title)
        path = unquote(urlsplit(url).path).lower()
        if PurePosixPath(path).suffix in UNSUPPORTED_EXTENSIONS:
            return UrlDecision(UrlDisposition.SKIPPED, "unsupported_extension", score)
        if not homepage and self._exclude.apply(url.lower()):
            return UrlDecision(UrlDisposition.SKIPPED, "excluded_pattern", score)
        if not self.scope.allows(url):
            if score > 0:
                return UrlDecision(UrlDisposition.EXTERNAL, "domain_not_approved", score)
            return UrlDecision(UrlDisposition.SKIPPED, "irrelevant_external", score)
        if not homepage and score < self.settings.minimum_relevance_score:
            return UrlDecision(UrlDisposition.SKIPPED, "below_relevance_threshold", score)
        return UrlDecision(UrlDisposition.PENDING, None, score)

"""Contract implemented by every crawler provider."""

from abc import ABC, abstractmethod

from models.crawl_result import CompetitorURL, CrawlResult


class BaseCrawler(ABC):
    @abstractmethod
    async def crawl(self, competitor: CompetitorURL) -> CrawlResult:
        """Traverse a competitor site and return normalized source pages."""
        raise NotImplementedError

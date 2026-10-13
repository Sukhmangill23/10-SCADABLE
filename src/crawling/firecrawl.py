"""Firecrawl adapter placeholder; importing it does not require its SDK."""

from config import Settings
from crawling.base import BaseCrawler
from models.crawl_result import CompetitorURL, CrawlResult


class FirecrawlCrawler(BaseCrawler):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def crawl(self, competitor: CompetitorURL) -> CrawlResult:
        # TODO: Add the Firecrawl SDK and validate its API key at execution time.
        # TODO: Implement page traversal, crawl limits, and extraction.
        # TODO: Map provider output to ScrapedContent and CrawlResult.
        raise NotImplementedError("Firecrawl crawling is not implemented yet.")

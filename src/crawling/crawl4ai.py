"""Crawl4AI adapter placeholder; no browser is launched by this module."""

from config import Settings
from crawling.base import BaseCrawler
from models.crawl_result import CompetitorURL, CrawlResult


class Crawl4AICrawler(BaseCrawler):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def crawl(self, competitor: CompetitorURL) -> CrawlResult:
        # TODO: Add the Crawl4AI SDK and manage its async browser lifecycle.
        # TODO: Implement page traversal, crawl limits, and extraction.
        # TODO: Map provider output to ScrapedContent and CrawlResult.
        raise NotImplementedError("Crawl4AI crawling is not implemented yet.")

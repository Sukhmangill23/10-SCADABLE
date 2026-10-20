"""Select an adapter without exposing provider details to the pipeline."""

from config import Settings
from crawling.base import BaseCrawler
from crawling.crawl4ai import Crawl4AICrawler
from crawling.firecrawl import FirecrawlCrawler


def create_crawler(settings: Settings) -> BaseCrawler:
    """Construct the configured adapter without starting a crawl."""
    if settings.crawler_provider == "firecrawl":
        return FirecrawlCrawler(settings)
    return Crawl4AICrawler(settings)

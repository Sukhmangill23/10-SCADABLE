"""Crawler interface, adapters, and realistic mock fixtures.

Enables the research orchestrator to execute against real Crawl4AI instances
when installed, or fall back to high-fidelity mock fixtures during offline
development and automated testing.
"""

from datetime import datetime, timezone
from typing import Any, Protocol


class CrawlerProtocol(Protocol):
    """Protocol defining the scraper interface expected by the orchestrator."""

    async def crawl(
        self,
        competitor_name: str,
        website_url: str,
    ) -> dict[str, Any]: ...


class MockCrawl4AICrawler:
    """Mock crawler returning realistic compliance SaaS crawl data.

    Simulates the subpage extraction (/features, /pricing, /docs) of Crawl4AI
    without requiring headless browser binaries or external network requests.
    """

    def __init__(self, should_fail: bool = False, delay_seconds: float = 0.0) -> None:
        self.should_fail = should_fail
        self.delay_seconds = delay_seconds

    async def crawl(
        self,
        competitor_name: str,
        website_url: str,
    ) -> dict[str, Any]:
        import asyncio

        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)

        if self.should_fail:
            raise RuntimeError(
                f"Mock crawler simulated failure while crawling '{website_url}'."
            )

        base_url = website_url.rstrip("/")
        scraped_at = datetime.now(timezone.utc).isoformat()

        return {
            "competitor_name": competitor_name,
            "base_url": base_url,
            "scraped_at": scraped_at,
            "pages": [
                {
                    "url": f"{base_url}/features",
                    "title": f"{competitor_name} - Platform Features",
                    "text": (
                        f"{competitor_name} provides automated compliance for SOC 2, "
                        "ISO 27001, and HIPAA. Features include continuous evidence "
                        "collection, vendor risk management, access reviews, and "
                        "over 75 cloud integrations including AWS, Azure, and Google Cloud."
                    ),
                },
                {
                    "url": f"{base_url}/pricing",
                    "title": f"{competitor_name} - Pricing Plans",
                    "text": (
                        f"{competitor_name} plans start at $7,500/year for single-framework "
                        "startups, scaling to $25,000+/year for enterprise multi-framework "
                        "packages with dedicated auditor support."
                    ),
                },
                {
                    "url": f"{base_url}/docs",
                    "title": f"{competitor_name} - Developer Documentation",
                    "text": (
                        f"Integration documentation for {competitor_name} REST API and "
                        "agent-based evidence collectors. Does not offer native "
                        "automated code remediation or EU Cyber Resilience Act (CRA) workflows."
                    ),
                },
            ],
        }


class Crawl4AIAdapter:
    """Adapter wrapping Yash & Jaynik's Crawl4AI implementation.

    Delegates to the Crawl4AI crawler when available in the environment.
    """

    def __init__(self) -> None:
        self._underlying: Any = None

    async def crawl(
        self,
        competitor_name: str,
        website_url: str,
    ) -> dict[str, Any]:
        # Attempt to dynamically import the Crawl4AI module if available
        try:
            from crawling.crawl4ai import Crawl4AICrawler
            from models.crawl_result import CompetitorURL
            from config import Settings

            crawler = Crawl4AICrawler(Settings())
            comp = CompetitorURL(name=competitor_name, url=website_url)
            result = await crawler.crawl(comp)

            # Normalize CrawlResult object to standard dict
            return {
                "competitor_name": competitor_name,
                "base_url": website_url,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "pages": [
                    {
                        "url": str(page.url),
                        "title": getattr(page, "title", None),
                        "text": getattr(page, "text", ""),
                    }
                    for page in getattr(result, "pages", [])
                ],
            }
        except (ImportError, NotImplementedError) as exc:
            # Fall back to mock crawler if Crawl4AI is not yet installed / implemented
            mock = MockCrawl4AICrawler()
            return await mock.crawl(competitor_name, website_url)


def get_default_crawler() -> CrawlerProtocol:
    """Return the default crawler adapter."""
    return Crawl4AIAdapter()


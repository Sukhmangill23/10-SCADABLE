"""LLM synthesis interface, adapters, and realistic mock fixtures.

Enables the research orchestrator to invoke OpenAI-based competitor SWOT
comparison against SCADABLE's baseline context, or fall back to high-fidelity
mock analysis during offline testing.
"""

from typing import Any, Protocol


class AnalyzerProtocol(Protocol):
    """Protocol defining the analysis interface expected by the orchestrator."""

    async def analyze(
        self,
        scraped_data: dict[str, Any],
        baseline_context: dict[str, Any],
    ) -> dict[str, Any]: ...


class MockOpenAIAnalyzer:
    """Mock analyzer returning realistic SWOT findings with citations.

    Produces structured compliance SWOT findings comparing competitor capabilities
    against SCADABLE's static baseline profile.
    """

    def __init__(self, should_fail: bool = False, delay_seconds: float = 0.0) -> None:
        self.should_fail = should_fail
        self.delay_seconds = delay_seconds

    async def analyze(
        self,
        scraped_data: dict[str, Any],
        baseline_context: dict[str, Any],
    ) -> dict[str, Any]:
        import asyncio

        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)

        if self.should_fail:
            raise RuntimeError(
                "Mock analyzer simulated failure during OpenAI SWOT synthesis."
            )

        competitor_name = scraped_data.get("competitor_name", "Competitor")
        base_url = scraped_data.get("base_url", "https://example.com")
        features_url = f"{base_url}/features"
        pricing_url = f"{base_url}/pricing"
        docs_url = f"{base_url}/docs"

        return {
            "competitor_name": competitor_name,
            "summary": (
                f"{competitor_name} is an established compliance automation platform "
                "supporting SOC 2, ISO 27001, and HIPAA with wide cloud integration coverage."
            ),
            "swot_entries": [
                {
                    "category": "strength",
                    "content": (
                        f"{competitor_name} has broad pre-built integrations with major "
                        "cloud providers and common developer tools."
                    ),
                    "source_url": features_url,
                },
                {
                    "category": "strength",
                    "content": (
                        f"Established market presence and strong auditor partner network "
                        "for fast SOC 2 Type II sign-offs."
                    ),
                    "source_url": features_url,
                },
                {
                    "category": "weakness",
                    "content": (
                        f"High annual starting pricing and enterprise-heavy tiers ($7.5k to $25k+) "
                        "create friction for early-stage startups."
                    ),
                    "source_url": pricing_url,
                },
                {
                    "category": "weakness",
                    "content": (
                        f"{competitor_name} lacks automated code remediation and native EU Cyber "
                        "Resilience Act (CRA) workflows."
                    ),
                    "source_url": docs_url,
                },
                {
                    "category": "opportunity",
                    "content": (
                        "SCADABLE can position itself as the cost-effective developer alternative "
                        "with direct code fixes and European regulatory coverage."
                    ),
                    "source_url": pricing_url,
                },
                {
                    "category": "threat",
                    "content": (
                        f"Large competitor marketing budgets and entrenched partner relationships "
                        "raise customer acquisition hurdles."
                    ),
                    "source_url": features_url,
                },
            ],
        }


class OpenAIAdapter:
    """Adapter wrapping Yash & Jaynik's OpenAI analysis engine.

    Delegates to the LLM analyzer when available; falls back to mock analysis.
    """

    def __init__(self) -> None:
        self._underlying: Any = None

    async def analyze(
        self,
        scraped_data: dict[str, Any],
        baseline_context: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            from llm.analyzer import Analyzer
            from llm.client import OpenAIClient
            from llm.schemas import AnalysisInput
            from models.crawl_result import ScrapedContent

            client = OpenAIClient()
            analyzer = Analyzer(client)

            pages = [
                ScrapedContent(
                    url=p.get("url", ""),
                    title=p.get("title"),
                    text=p.get("text", ""),
                )
                for p in scraped_data.get("pages", [])
            ]
            analysis_input = AnalysisInput(
                company_name=scraped_data.get("competitor_name", "Unknown"),
                pages=pages,
            )
            facts = await analyzer.extract_information(analysis_input)
            result = await analyzer.analyze_competitor(facts)

            # Map CompanyAnalysis output into SWOT entries
            entries = []
            source_urls = getattr(result, "source_urls", [])
            primary_source = source_urls[0] if source_urls else None

            for s in getattr(result, "strengths", []):
                entries.append({"category": "strength", "content": s, "source_url": primary_source})
            for w in getattr(result, "weaknesses", []):
                entries.append({"category": "weakness", "content": w, "source_url": primary_source})

            return {
                "competitor_name": getattr(result, "company_name", ""),
                "summary": getattr(result, "summary", ""),
                "swot_entries": entries,
            }
        except (ImportError, NotImplementedError):
            mock = MockOpenAIAnalyzer()
            return await mock.analyze(scraped_data, baseline_context)


def get_default_analyzer() -> AnalyzerProtocol:
    """Return the default analysis adapter."""
    return OpenAIAdapter()


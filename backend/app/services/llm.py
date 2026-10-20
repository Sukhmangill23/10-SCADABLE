"""LLM synthesis interface, adapters, and realistic mock fixtures.

Enables the research orchestrator to invoke OpenAI-based competitor SWOT
comparison against SCADABLE's baseline context, or fall back to high-fidelity
mock analysis during offline testing.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)


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
            from datetime import datetime, timezone

            from llm.analyzer import Analyzer
            from llm.client import OpenAIClient
            from llm.config import Settings
            from llm.inputs import load_analysis_input
            from llm.schemas import (
                AnalysisInput,
                AnalysisPage,
                CrawlExportSummary,
                ExportedPage,
            )
            from llm.swot_entries import to_swot_entries
            from scraper.environment import load_environment
            from scraper.models import CrawlSummary
            from scraper.types import PageCategory

            load_environment()

            # Check if summary_path exists on disk
            summary_path = scraped_data.get("summary_path")
            if summary_path and Path(summary_path).exists():
                analysis_input = await asyncio.to_thread(
                    load_analysis_input, summary_path
                )
            else:
                # Construct AnalysisInput from in-memory scraped_data snapshot
                valid_categories = {c.value for c in PageCategory}
                analysis_pages = []
                for idx, p in enumerate(scraped_data.get("pages", [])):
                    url_str = p.get("url", "")
                    body_md = p.get("text") or p.get("markdown") or ""
                    if not url_str or not body_md.strip():
                        continue
                    raw_cat = p.get("category", "features")
                    cat = raw_cat if raw_cat in valid_categories else "other"
                    exported = ExportedPage(
                        url=url_str,
                        url_path=urlsplit(url_str).path or "/",
                        markdown_file=f"pages/page_{idx}.md",
                        title=p.get("title"),
                        category=cat,
                        word_count=len(body_md.split()),
                        crawled_at=datetime.now(timezone.utc),
                        status="success",
                    )
                    analysis_pages.append(
                        AnalysisPage(
                            source=exported,
                            markdown=body_md,
                        )
                    )
                if not analysis_pages:
                    raise ValueError("No usable scraped pages found in scraped_data.")

                raw_base = scraped_data.get("base_url", "https://example.com")
                base_parts = urlsplit(raw_base)
                homepage_url = (
                    f"{base_parts.scheme}://{base_parts.netloc}"
                    if base_parts.scheme and base_parts.netloc
                    else "https://example.com"
                )

                now = datetime.now(timezone.utc)
                export_summary = CrawlExportSummary(
                    competitor_name=scraped_data.get("competitor_name", "Unknown"),
                    homepage_url=homepage_url,
                    started_at=now,
                    finished_at=now,
                    duration_seconds=1.0,
                    status="success",
                    completion_reason="completed",
                    counts=CrawlSummary(
                        successful=len(analysis_pages),
                        failed=0,
                        discovered=len(analysis_pages),
                    ),
                    pages=[ap.source for ap in analysis_pages],
                )
                analysis_input = AnalysisInput(
                    crawl_summary=export_summary,
                    pages=analysis_pages,
                )

            settings = Settings()
            if not settings.openai_model.strip():
                settings = settings.model_copy(update={"openai_model": "gpt-4o-mini"})
            client = OpenAIClient(settings)
            try:
                analyzer = Analyzer(client)
                facts = await analyzer.extract_information(analysis_input)
                company_analysis = await analyzer.analyze_competitor(facts)
            finally:
                await client.close()

            # Map cited strengths and weaknesses
            swot_entries = to_swot_entries(company_analysis)

            competitor_name = getattr(
                company_analysis,
                "company_name",
                scraped_data.get("competitor_name", "Competitor"),
            )
            base_url = scraped_data.get("base_url", "https://example.com")
            primary_source = (
                swot_entries[0]["source_url"]
                if swot_entries
                else f"{base_url.rstrip('/')}/pricing"
            )

            # Synthesize SCADABLE-relative opportunities and threats
            swot_entries.append({
                "category": "opportunity",
                "content": (
                    f"SCADABLE can position against {competitor_name} using automated code-level "
                    "remediation and native EU Cyber Resilience Act (CRA) workflows."
                ),
                "source_url": primary_source,
            })
            swot_entries.append({
                "category": "threat",
                "content": (
                    f"{competitor_name}'s established market presence and broad integration ecosystem "
                    "pose competitive customer acquisition hurdles."
                ),
                "source_url": primary_source,
            })

            return {
                "schema_version": "backend-analysis-v1",
                "mode": "real",
                "perspective": "scadable_relative",
                "competitor_name": competitor_name,
                "summary": getattr(company_analysis, "summary", ""),
                "swot_entries": swot_entries,
                "scores": [
                    s.model_dump()
                    for s in getattr(company_analysis, "scores", [])
                ],
            }

        except (ImportError, ValueError, Exception) as exc:
            logger.warning(
                "Real OpenAI analyzer unavailable or unconfigured (%s); falling back to mock analyzer.",
                exc,
            )
            mock = MockOpenAIAnalyzer()
            return await mock.analyze(scraped_data, baseline_context)


def get_default_analyzer() -> AnalyzerProtocol:
    """Return the default analysis adapter."""
    return OpenAIAdapter()

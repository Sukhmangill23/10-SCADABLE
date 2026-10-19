"""LLM synthesis interface, adapters, and realistic mock fixtures.

Enables the research orchestrator to invoke OpenAI-based competitor SWOT
comparison against SCADABLE's baseline context, or fall back to high-fidelity
mock analysis during offline testing.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Protocol

from app.llm.analyzer import Analyzer, ProgressCallback
from app.llm.client import LLMClientProtocol, OpenAIClient
from app.llm.config import LLMSettings
from app.llm.validation import to_swot_entries
from app.llm.versioning import build_versions

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

        base_result: dict[str, Any] = {
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
        return _extend_mock_result(base_result, scraped_data, baseline_context)


def _extend_mock_result(
    base_result: dict[str, Any],
    scraped_data: dict[str, Any],
    baseline_context: dict[str, Any],
) -> dict[str, Any]:
    """Add the real analyzer's additive keys so mock output has the same shape."""
    entries = base_result["swot_entries"]
    findings = [
        {
            "category": e["category"],
            "content": e["content"],
            "status": "confirmed",
            "source_urls": [e["source_url"]] if e.get("source_url") else [],
        }
        for e in entries
    ]
    pages = [p for p in scraped_data.get("pages") or [] if isinstance(p, dict)]
    return {
        "competitor_name": base_result["competitor_name"],
        "summary": base_result["summary"],
        "swot_entries": to_swot_entries(findings),
        "analysis_mode": "mock",
        "profile": {
            "company_name": base_result["competitor_name"],
            "summary": base_result["summary"],
            "target_customers": [],
            "frameworks": ["SOC 2", "ISO 27001", "HIPAA"],
            "key_features": [],
            "integrations": [],
            "pricing_summary": None,
            "source_urls": [],
        },
        "signals": [],
        "findings": findings,
        "facts": [],
        "missing_topics": [],
        "scadable_analysis": None,
        "sources": [{"url": p.get("url"), "title": p.get("title")} for p in pages],
        "versions": build_versions(scraped_data, baseline_context, "mock"),
        "usage": {
            "model": "mock",
            "stages": {},
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_input_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
            "pricing_configured": False,
            "preflight_estimate_usd": 0.0,
        },
        "warnings": ["Mock analysis: findings are canned fixtures, not real research."],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


class AnalyzerUnavailableError(RuntimeError):
    """Raised when the real analyzer is not configured and mock is disallowed."""


class OpenAIAdapter:
    """Orchestrator-facing adapter around the real LLM comparison engine.

    Uses ``app.llm.analyzer.Analyzer`` when ``OPENAI_API_KEY`` and
    ``OPENAI_MODEL`` are set. Otherwise it falls back to mock analysis with a
    loud warning and ``analysis_mode="mock"`` in the result, unless
    ``LLM_ALLOW_MOCK=false``, in which case it raises so the run fails.
    Real API errors always propagate (the run fails and prior findings stay).
    """

    def __init__(
        self,
        settings: LLMSettings | None = None,
        client: LLMClientProtocol | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.settings = settings
        self.client = client
        self.progress_callback = progress_callback

    async def analyze(
        self,
        scraped_data: dict[str, Any],
        baseline_context: dict[str, Any],
    ) -> dict[str, Any]:
        settings = self.settings or LLMSettings()
        client = self.client
        owns_client = False

        if client is None:
            if not settings.is_configured():
                reason = "OPENAI_API_KEY and/or OPENAI_MODEL are not set"
                if not settings.llm_allow_mock:
                    raise AnalyzerUnavailableError(
                        f"Real LLM analysis unavailable: {reason} and LLM_ALLOW_MOCK=false."
                    )
                logger.warning(
                    "!!! MOCK ANALYSIS IN USE !!! %s; returning canned SWOT for %r. "
                    "Do not present these results as real.",
                    reason,
                    scraped_data.get("competitor_name"),
                )
                result = await MockOpenAIAnalyzer().analyze(scraped_data, baseline_context)
                result["warnings"] = [f"Mock analysis used: {reason}."] + result.get(
                    "warnings", []
                )
                return result
            client = OpenAIClient(settings)
            owns_client = True

        analyzer = Analyzer(client, settings, self.progress_callback)
        try:
            return await analyzer.run(scraped_data, baseline_context)
        finally:
            if owns_client:
                await client.close()


def get_default_analyzer() -> AnalyzerProtocol:
    """Return the default analysis adapter."""
    return OpenAIAdapter()


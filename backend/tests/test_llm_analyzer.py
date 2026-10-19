"""Tests for the LLM comparison engine, using a fake client (no network)."""

import asyncio
import logging

import pytest

from app.core.baseline import get_scadable_baseline
from app.llm.analyzer import (
    AnalysisError,
    Analyzer,
    BudgetExceeded,
    CostLimitExceeded,
    EmptyInputError,
    clear_scadable_cache,
    prepare_pages,
)
from app.llm.client import StructuredResult
from app.llm.config import LLMSettings
from app.llm.schemas import (
    CompanyAnalysis,
    CompetitiveSignal,
    CompetitorProfile,
    ComparisonResult,
    ExtractedFact,
    ExtractedInformation,
    SWOTFinding,
)
from app.services.crawler import MockCrawl4AICrawler
from app.services.llm import AnalyzerUnavailableError, OpenAIAdapter

BASE = "https://vanta.com"
HALLUCINATED = "https://vanta.com/made-up-page"


def _extracted() -> ExtractedInformation:
    return ExtractedInformation(
        company_name="Vanta",
        summary="Vanta automates SOC 2 and ISO 27001.",
        frameworks=["SOC 2", "ISO 27001", "HIPAA"],
        features=["Continuous monitoring"],
        integrations=["AWS"],
        target_customers=["Startups"],
        pricing_summary="Starts at $7,500/year.",
        facts=[
            ExtractedFact(
                topic="frameworks",
                statement="Supports SOC 2.",
                source_url=f"{BASE}/features",
                evidence_quote="automated compliance for SOC 2",
            ),
            ExtractedFact(
                topic="pricing",
                statement="Invented page.",
                source_url=HALLUCINATED,
                evidence_quote="n/a",
            ),
        ],
        missing_topics=["regulatory_coverage"],
        source_urls=[f"{BASE}/features"],
    )


def _scadable() -> CompanyAnalysis:
    return CompanyAnalysis(
        company_name="SCADABLE",
        summary="Compliance automation.",
        strengths=["EU CRA coverage"],
        weaknesses=["No stated auditor network"],
        source_urls=[],
    )


def _comparison() -> ComparisonResult:
    return ComparisonResult(
        profile=CompetitorProfile(
            company_name="Vanta",
            summary="Vanta is a compliance automation platform.",
            target_customers=["Startups"],
            frameworks=["SOC 2"],
            key_features=["Continuous monitoring"],
            integrations=["AWS"],
            pricing_summary="Starts at $7,500/year.",
            source_urls=[f"{BASE}/pricing", HALLUCINATED],
        ),
        signals=[
            CompetitiveSignal(
                dimension="eu_regulation",
                competitor_position="No CRA support found.",
                scadable_position="Native CRA tracking.",
                advantage="scadable",
                status="not_found",
                source_urls=[f"{BASE}/docs/"],  # trailing slash still matches
            )
        ],
        swot=[
            SWOTFinding(
                category="strength",
                content="Vanta supports SOC 2, ISO 27001 and HIPAA.",
                status="confirmed",
                source_urls=[f"{BASE}/features"],
            ),
            SWOTFinding(
                category="weakness",
                content="No EU CRA workflow found on crawled pages.",
                status="not_found",
                source_urls=[],
            ),
            SWOTFinding(
                category="opportunity",
                content="SCADABLE can lead on EU CRA.",
                status="confirmed",
                source_urls=[HALLUCINATED],  # only citation is fake -> unverified
            ),
            SWOTFinding(
                category="threat",
                content="Vanta's integration breadth raises switching costs.",
                status="confirmed",
                source_urls=[f"https://WWW.vanta.com/features/#top", HALLUCINATED],
            ),
        ],
    )


class FakeClient:
    """Returns canned outputs per schema and records calls."""

    def __init__(
        self,
        fail_on: type | None = None,
        model: str = "gpt-5.6-luna",
        output_tokens: int = 200,
    ) -> None:
        self.calls: list[tuple[type, str | None]] = []
        self.fail_on = fail_on
        self.model = model
        self.output_tokens = output_tokens
        self.closed = False

    async def generate_structured(self, *, instructions, input_text, output_schema, cache_key=None):
        self.calls.append((output_schema, cache_key))
        if output_schema is self.fail_on:
            raise RuntimeError("simulated API error")
        output = {
            ExtractedInformation: _extracted,
            CompanyAnalysis: _scadable,
            ComparisonResult: _comparison,
        }[output_schema]()
        return StructuredResult(output=output, input_tokens=1000,
                                output_tokens=self.output_tokens,
                                cached_input_tokens=100, cache_write_tokens=50)

    async def close(self) -> None:
        self.closed = True


def _settings(**overrides) -> LLMSettings:
    values = {"openai_api_key": None, "openai_model": "", "llm_allow_mock": True}
    values.update(overrides)
    return LLMSettings(_env_file=None, **values)


@pytest.fixture(autouse=True)
def _reset_cache():
    clear_scadable_cache()
    yield
    clear_scadable_cache()


@pytest.fixture
def scraped():
    return asyncio.run(MockCrawl4AICrawler().crawl("Vanta", BASE))


def test_prepare_pages_tolerates_shapes_and_trims():
    data = {
        "pages": [
            {"url": "https://a.com/1", "markdown": "x" * 50, "extra": 1},
            {"url": "https://a.com/2", "content": "y" * 50},
            {"url": "", "text": "no url"},
            {"url": "https://a.com/3"},
            "not a dict",
        ]
    }
    pages = prepare_pages(data, max_chars_per_page=30, max_total_chars=40)
    assert [p.url for p in pages] == ["https://a.com/1", "https://a.com/2"]
    assert len(pages[0].text) == 30 and len(pages[1].text) == 10


def test_full_run_shape_and_validation(scraped):
    events = []
    client = FakeClient()
    analyzer = Analyzer(client, _settings(), events.append)
    result = asyncio.run(analyzer.run(scraped, get_scadable_baseline()))

    # Backward-compatible keys
    assert result["competitor_name"] == "Vanta"
    assert result["summary"]
    entries = result["swot_entries"]
    assert {e["category"] for e in entries} == {"strength", "weakness", "opportunity", "threat"}
    for e in entries:
        assert set(e) >= {"category", "content", "source_url"}
        assert e["source_url"] is None or e["source_url"].startswith(BASE)

    by_cat = {f["category"]: f for f in result["findings"]}
    assert by_cat["strength"]["status"] == "confirmed"
    assert by_cat["weakness"]["status"] == "not_found"
    assert by_cat["opportunity"]["status"] == "unverified"
    assert by_cat["opportunity"]["source_urls"] == []
    # Normalized match maps back to the crawled URL; fake URL dropped.
    assert by_cat["threat"]["source_urls"] == [f"{BASE}/features"]
    assert HALLUCINATED not in str(result["profile"]) + str(result["signals"])
    assert result["signals"][0]["source_urls"] == [f"{BASE}/docs"]
    assert all(f["source_url"] != HALLUCINATED for f in result["facts"])
    assert any("Dropped" in w for w in result["warnings"])

    assert result["analysis_mode"] == "real"
    assert result["versions"]["model"] == "gpt-5.6-luna"
    assert len(result["versions"]["cache_key"]) == 64
    usage = result["usage"]
    assert usage["input_tokens"] == 3000 and usage["output_tokens"] == 600
    # Per request: 850 uncached, 100 cached, 50 cache-write input; 200 output.
    per_request = (850 * 0.20 + 100 * 0.02 + 50 * 0.25 + 200 * 1.20) / 1e6
    assert usage["estimated_cost_usd"] == pytest.approx(3 * per_request, abs=1e-6)
    assert set(usage["stages"]) == {"extract", "scadable", "compare"}
    assert usage["aborted"] is False and usage["max_run_cost_usd"] == 0.25
    assert 0 < usage["preflight_estimate_usd"] < 0.25

    statuses = [(e["stage"], e["status"]) for e in events]
    for stage in ("extract", "scadable", "compare", "validate"):
        assert (stage, "queued") in statuses
        assert (stage, "running") in statuses
        assert (stage, "completed") in statuses


def test_scadable_analysis_is_memoized(scraped):
    client = FakeClient()
    asyncio.run(Analyzer(client, _settings()).run(scraped, get_scadable_baseline()))
    asyncio.run(Analyzer(client, _settings()).run(scraped, get_scadable_baseline()))
    assert sum(1 for schema, _ in client.calls if schema is CompanyAnalysis) == 1


def test_stage_failure_emits_failed_event(scraped):
    events = []
    analyzer = Analyzer(FakeClient(fail_on=ComparisonResult), _settings(), events.append)
    with pytest.raises(AnalysisError, match="simulated") as info:
        asyncio.run(analyzer.run(scraped, get_scadable_baseline()))
    assert ("compare", "failed") in [(e["stage"], e["status"]) for e in events]
    # Tokens spent by the stages that did run are still reported.
    assert info.value.usage["input_tokens"] == 2000
    assert info.value.usage["estimated_cost_usd"] > 0


def test_empty_pages_raise(scraped):
    with pytest.raises(EmptyInputError):
        asyncio.run(Analyzer(FakeClient(), _settings()).run(
            {"competitor_name": "X", "pages": []}, get_scadable_baseline()))


def test_cost_guard_blocks_before_any_call(scraped):
    client = FakeClient()
    settings = _settings(max_run_cost_usd=0.000001)
    with pytest.raises(CostLimitExceeded) as info:
        asyncio.run(Analyzer(client, settings).run(scraped, get_scadable_baseline()))
    assert client.calls == []
    assert info.value.usage["aborted"] is True
    assert "MAX_RUN_COST_USD" in info.value.usage["abort_reason"]
    assert info.value.usage["estimated_cost_usd"] == 0


def test_cost_guard_aborts_mid_run_on_real_spend(scraped):
    # Huge outputs from the first stages push real spend past the cap.
    client = FakeClient(output_tokens=150_000)
    with pytest.raises(CostLimitExceeded, match="skipped compare") as info:
        asyncio.run(Analyzer(client, _settings()).run(scraped, get_scadable_baseline()))
    assert ComparisonResult not in [schema for schema, _ in client.calls]
    assert info.value.usage["aborted"] is True
    assert info.value.usage["estimated_cost_usd"] > 0.25


def test_project_budget_blocks_run(scraped):
    client = FakeClient()
    analyzer = Analyzer(client, _settings(project_budget_usd=100.0),
                        spend_provider=lambda: 99.999)
    with pytest.raises(BudgetExceeded) as info:
        asyncio.run(analyzer.run(scraped, get_scadable_baseline()))
    assert client.calls == []
    assert info.value.usage["project_budget"]["allowed"] is False


def test_project_budget_recorded_and_warns(scraped, caplog):
    analyzer = Analyzer(FakeClient(), _settings(), spend_provider=lambda: 60.0)
    with caplog.at_level(logging.WARNING):
        result = asyncio.run(analyzer.run(scraped, get_scadable_baseline()))
    budget = result["usage"]["project_budget"]
    assert budget["allowed"] is True and budget["thresholds_crossed"] == [0.5]
    assert "past the 50% threshold" in caplog.text


def test_unknown_model_has_null_cost_and_skips_cap(scraped, caplog):
    with caplog.at_level(logging.WARNING):
        result = asyncio.run(Analyzer(FakeClient(model="other"), _settings()).run(
            scraped, get_scadable_baseline()))
    assert result["usage"]["estimated_cost_usd"] is None
    assert "No pricing for model" in caplog.text


def test_adapter_uses_real_analyzer_with_injected_client(scraped):
    adapter = OpenAIAdapter(settings=_settings(), client=FakeClient())
    result = asyncio.run(adapter.analyze(scraped, get_scadable_baseline()))
    assert result["analysis_mode"] == "real"


def test_adapter_falls_back_to_mock_loudly(scraped, caplog):
    adapter = OpenAIAdapter(settings=_settings())
    with caplog.at_level(logging.WARNING):
        result = asyncio.run(adapter.analyze(scraped, get_scadable_baseline()))
    assert result["analysis_mode"] == "mock"
    assert "MOCK ANALYSIS IN USE" in caplog.text
    assert result["warnings"][0].startswith("Mock analysis used")
    assert {e["category"] for e in result["swot_entries"]} == {
        "strength", "weakness", "opportunity", "threat"}


def test_adapter_refuses_mock_when_disallowed(scraped):
    adapter = OpenAIAdapter(settings=_settings(llm_allow_mock=False))
    with pytest.raises(AnalyzerUnavailableError):
        asyncio.run(adapter.analyze(scraped, get_scadable_baseline()))

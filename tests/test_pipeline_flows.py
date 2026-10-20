"""Check the SCADABLE, competitor and comparison flows with offline test doubles."""

import asyncio

import pytest

import pipeline
from crawling.base import BaseCrawler
from llm.analyzer import Analyzer
from llm.schemas import (
    AnalysisInput,
    CompanyAnalysis,
    ComparisonInput,
    CompetitorNote,
    ExtractedInformation,
    SWOTAnalysis,
)
from models.crawl_result import CompetitorURL, CrawlResult, ScrapedContent

SCADABLE = CompetitorURL(name="SCADABLE", url="https://scadable.com")
CLUELY = CompetitorURL(name="Cluely", url="https://cluely.com")
BLUEJ = CompetitorURL(name="Blue J", url="https://www.bluej.com")


class StubCrawler(BaseCrawler):
    """Return one page per company, or no pages for hosts listed in `empty`."""

    def __init__(self, empty=()):
        self.empty = set(empty)
        self.crawled = []

    async def crawl(self, competitor: CompetitorURL) -> CrawlResult:
        self.crawled.append(competitor.name)
        pages = []
        if competitor.name not in self.empty:
            pages = [ScrapedContent(url=competitor.url, text=f"  {competitor.name} page  ")]
        return CrawlResult(competitor=competitor, provider="crawl4ai", pages=pages)


class StubAnalyzer(Analyzer):
    def __init__(self, fail_for=()):
        # No SDK client is needed by this test double.
        self.fail_for = set(fail_for)
        self.calls = []
        self.comparison_input = None

    async def extract_information(self, data: AnalysisInput) -> ExtractedInformation:
        self.calls.append(("extract", data.company_name))
        # Cleaning runs before extraction, so the page text must already be stripped.
        assert data.pages[0].text == f"{data.company_name} page"
        return ExtractedInformation(
            company_name=data.company_name, summary="facts", claims_cited=[]
        )

    async def analyze_competitor(self, data: ExtractedInformation) -> CompanyAnalysis:
        self.calls.append(("competitor", data.company_name))
        if data.company_name in self.fail_for:
            raise RuntimeError(f"analysis failed for {data.company_name}")
        return _analysis(data.company_name, "competitor")

    async def analyze_scadable(self, data: ExtractedInformation) -> CompanyAnalysis:
        self.calls.append(("scadable", data.company_name))
        return _analysis(data.company_name, "scadable")

    async def compare(self, data: ComparisonInput) -> SWOTAnalysis:
        self.calls.append(("compare", None))
        self.comparison_input = data
        return SWOTAnalysis(
            strengths=["s"],
            weaknesses=["w"],
            opportunities=["o"],
            threats=["t"],
            competitor_notes=[
                CompetitorNote(company_name=c.company_name, why_it_matters=f"{c.company_name} matters")
                for c in data.competitors
            ],
        )


def _analysis(name: str, kind: str) -> CompanyAnalysis:
    return CompanyAnalysis(company_name=name, summary=kind, claims_cited=[], scores=[])


def test_run_scadable_uses_the_scadable_analysis():
    crawler, analyzer = StubCrawler(), StubAnalyzer()
    result = asyncio.run(pipeline.run_scadable(SCADABLE, crawler=crawler, analyzer=analyzer))
    assert result.summary == "scadable"
    assert crawler.crawled == ["SCADABLE"]
    assert analyzer.calls == [("extract", "SCADABLE"), ("scadable", "SCADABLE")]


@pytest.mark.parametrize("run", [pipeline.run_scadable, pipeline.run_competitor])
def test_company_without_pages_is_rejected_before_any_llm_call(run):
    crawler = StubCrawler(empty={"SCADABLE", "Cluely"})
    analyzer = StubAnalyzer()
    company = SCADABLE if run is pipeline.run_scadable else CLUELY
    with pytest.raises(ValueError, match="No pages found"):
        asyncio.run(run(company, crawler=crawler, analyzer=analyzer))
    assert analyzer.calls == []


def test_run_comparison_passes_scadable_and_competitors_in_order():
    crawler, analyzer = StubCrawler(), StubAnalyzer()
    swot = asyncio.run(
        pipeline.run_comparison(
            SCADABLE, competitors=[CLUELY, BLUEJ], crawler=crawler, analyzer=analyzer
        )
    )
    assert swot.strengths == ["s"]
    # One note per competitor, in the same order as the input.
    assert [n.company_name for n in swot.competitor_notes] == ["Cluely", "Blue J"]
    data = analyzer.comparison_input
    assert data.scadable.company_name == "SCADABLE"
    assert data.scadable.summary == "scadable"
    assert [c.company_name for c in data.competitors] == ["Cluely", "Blue J"]
    assert {c.summary for c in data.competitors} == {"competitor"}
    # The comparison is the last step and runs exactly once.
    assert analyzer.calls[-1] == ("compare", None)
    assert [call for call, _ in analyzer.calls].count("compare") == 1
    assert sorted(crawler.crawled) == ["Blue J", "Cluely", "SCADABLE"]


def test_run_comparison_with_no_competitors_still_compares():
    analyzer = StubAnalyzer()
    asyncio.run(
        pipeline.run_comparison(
            SCADABLE, competitors=[], crawler=StubCrawler(), analyzer=analyzer
        )
    )
    assert analyzer.comparison_input.competitors == []


def test_run_comparison_fails_when_a_competitor_fails_and_skips_compare():
    analyzer = StubAnalyzer(fail_for={"Cluely"})
    with pytest.raises(RuntimeError, match="Cluely"):
        asyncio.run(
            pipeline.run_comparison(
                SCADABLE,
                competitors=[CLUELY, BLUEJ],
                crawler=StubCrawler(),
                analyzer=analyzer,
            )
        )
    assert ("compare", None) not in analyzer.calls

"""Use test doubles to verify the intended sequence and typed handoffs."""

import asyncio

import pytest

import pipeline
from crawling.base import BaseCrawler
from llm.analyzer import Analyzer
from llm.schemas import AnalysisInput, ClaimCited, CompanyAnalysis, ExtractedInformation
from models.crawl_result import CompetitorURL, CrawlResult, ScrapedContent


def test_pipeline_connects_crawl_clean_extract_and_analyze(monkeypatch):
    steps = []
    competitor = CompetitorURL(name="Example", url="https://example.com")
    raw = ScrapedContent(url=competitor.url, text="raw content")
    cleaned = raw.model_copy(update={"text": "clean content"})
    facts = ExtractedInformation(
        company_name=competitor.name,
        summary="Example facts",
        claims_cited=[
            ClaimCited(category="features", claim="Example claim", source_url=str(competitor.url))
        ],
    )
    analysis = CompanyAnalysis(
        company_name=competitor.name,
        summary="Example analysis",
        claims_cited=[
            ClaimCited(category="strength", claim="Example claim", source_url=str(competitor.url))
        ],    scores=[],
    )

    class StubCrawler(BaseCrawler):
        async def crawl(self, target: CompetitorURL) -> CrawlResult:
            assert target == competitor
            steps.append("crawl")
            return CrawlResult(competitor=target, provider="firecrawl", pages=[raw])

    def stub_clean(content: ScrapedContent) -> ScrapedContent:
        assert content == raw
        steps.append("clean")
        return cleaned

    class StubAnalyzer(Analyzer):
        def __init__(self) -> None:
            # No SDK client is needed by this test double.
            pass

        async def extract_information(self, data: AnalysisInput) -> ExtractedInformation:
            assert data == AnalysisInput(company_name=competitor.name, pages=[cleaned])
            steps.append("extract")
            return facts

        async def analyze_competitor(self, data: ExtractedInformation) -> CompanyAnalysis:
            assert data == facts
            steps.append("analyze")
            return analysis

    monkeypatch.setattr(pipeline, "clean_content", stub_clean)
    result = asyncio.run(
        pipeline.run_competitor(competitor, crawler=StubCrawler(), analyzer=StubAnalyzer())
    )
    assert result == analysis
    assert steps == ["crawl", "clean", "extract", "analyze"]


def test_clean_content_strips_whitespace_and_keeps_url():
    content = ScrapedContent(url="https://example.com", title="T", text="  hello\n\n")
    cleaned = pipeline.clean_content(content)
    assert cleaned.text == "hello"
    assert cleaned.url == content.url
    assert cleaned.title == "T"

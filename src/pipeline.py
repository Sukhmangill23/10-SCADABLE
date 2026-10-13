"""Skeleton connecting independently implementable research components."""

from crawling.base import BaseCrawler
from llm.analyzer import Analyzer
from llm.schemas import AnalysisInput, CompanyAnalysis
from models.crawl_result import CompetitorURL
from processing.cleaner import clean_content


async def run_pipeline(
    competitor: CompetitorURL,
    *,
    crawler: BaseCrawler,
    analyzer: Analyzer,
) -> CompanyAnalysis:
    """Show the data flow; concrete components currently raise NotImplementedError."""
    # TODO: Define empty-content handling and pipeline error reporting.
    # TODO: Add separate SCADABLE and comparison flows when requirements settle.
    result = await crawler.crawl(competitor)
    pages = [clean_content(page) for page in result.pages]
    data = AnalysisInput(company_name=competitor.name, pages=pages)
    facts = await analyzer.extract_information(data)
    return await analyzer.analyze_competitor(facts)

"""Skeleton connecting independently implementable research components."""
import asyncio

from crawling.base import BaseCrawler
from llm.analyzer import Analyzer
from llm.schemas import AnalysisInput, CompanyAnalysis, ComparisonInput
from models.crawl_result import CompetitorURL
from processing.cleaner import clean_content


async def run_competitor(
    competitor: CompetitorURL,
    *,
    crawler: BaseCrawler,
    analyzer: Analyzer,
) -> CompanyAnalysis:
    """Show the data flow; concrete components currently raise NotImplementedError."""
    result = await crawler.crawl(competitor)
    pages = [clean_content(page) for page in result.pages]
    if not pages:
        raise ValueError(f"No pages found associated with {competitor.url}!")
    data = AnalysisInput(company_name=competitor.name, pages=pages)
    facts = await analyzer.extract_information(data)
    return await analyzer.analyze_competitor(facts)


async def run_scadable(
        scadable: CompetitorURL,
        *,
        crawler: BaseCrawler,
        analyzer: Analyzer
) -> CompanyAnalysis:
    result = await crawler.crawl(scadable)
    pages = [clean_content(page) for page in result.pages]
    if not pages:
        raise ValueError(f"No pages found associated with {scadable.url}!")
    data = AnalysisInput(company_name=scadable.name, pages=pages)
    facts = await analyzer.extract_information(data)
    return await analyzer.analyze_scadable(facts)


async def run_comparison(scadable: CompetitorURL, *, competitors: list[CompetitorURL], crawler: BaseCrawler, analyzer: Analyzer):
    """
    Runs the comparison between SCADABLE and its competitors.
    """
    scadable_analysis, *competitor_analyses = await asyncio.gather(
        run_scadable(scadable, crawler=crawler, analyzer=analyzer),
        *(run_competitor(c, crawler=crawler, analyzer=analyzer) for c in competitors),
    )
    return await analyzer.compare(
        ComparisonInput(scadable=scadable_analysis, competitors=competitor_analyses)
    )
    
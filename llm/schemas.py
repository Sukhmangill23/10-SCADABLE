"""Source-backed analysis inputs and structured competitor insights."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from scraper import CrawlExportSummary, ExportedPage


class AnalysisPage(BaseModel):
    """One exported page's metadata alongside its unchanged Markdown."""

    source: ExportedPage
    markdown: str


class AnalysisInput(BaseModel):
    crawl_summary: CrawlExportSummary
    pages: list[AnalysisPage] = Field(min_length=1)

    @property
    def company_name(self) -> str:
        return self.crawl_summary.competitor_name


Category = Literal[
    "features",
    "target_customers",
    "pricing",
    "integrations",
    "differentiators",
    "strength",
    "weakness",
]


class ClaimCited(BaseModel):
    """One fact or finding about a company, with the page that supports it."""

    category: Category
    claim: str
    source_url: str


class FeatureScore(BaseModel):
    """How much competition one of a company's features brings to SCADABLE (0-10)."""

    feature: str
    score: int

    # A validator (not Field limits) keeps the range out of the JSON schema sent
    # to OpenAI, whose strict mode does not accept every numeric keyword.
    @field_validator("score")
    @classmethod
    def _score_in_range(cls, value: int) -> int:
        if not 0 <= value <= 10:
            raise ValueError("score must be between 0 and 10")
        return value

class PartialExtractedInformation(BaseModel):
    """A partial, token-effective shape for a company. Saves tokens and prevents the LLM from providing the wrong 
    company name when scraping, because the model sometimes echoes a placeholder name or invents its own."""
    summary: str
    summary_source_urls: list[str]
    # Every fact is one cited claim; read them back by category with claims_in().
    claims_cited: list[ClaimCited]

    
    def claims_in(self, category: Category) -> list[str]:
        return [c.claim for c in self.claims_cited if c.category == category]

class ExtractedInformation(PartialExtractedInformation):
    """Facts extracted from source pages before interpretation."""
    company_name: str


class PartialCompanyAnalysis(BaseModel):
    """A partial, token-effective shape for a competitor or SCADABLE. Used to fetch all the new 
    data for the company before packing it with the company name and summary."""

    claims_cited: list[ClaimCited]
    scores: list[FeatureScore]

class CompanyAnalysis(PartialCompanyAnalysis):
    """Shared analysis shape for a competitor or SCADABLE."""

    company_name: str
    summary: str
    summary_source_urls: list[str]
    # Strengths and weaknesses are claims with category "strength" or "weakness".
    claims_cited: list[ClaimCited]
    scores: list[FeatureScore]

    def claims_in(self, category: Category) -> list[str]:
        return [c.claim for c in self.claims_cited if c.category == category]

    @property
    def strengths(self) -> list[str]:
        return self.claims_in("strength")

    @property
    def weaknesses(self) -> list[str]:
        return self.claims_in("weakness")


class CompetitorResearchResult(BaseModel):
    """Analysis and extracted facts with the scraper's original run provenance."""

    crawl_summary: CrawlExportSummary
    extracted_information: ExtractedInformation
    analysis: CompanyAnalysis


class ComparisonInput(BaseModel):
    scadable: CompanyAnalysis
    competitors: list[CompanyAnalysis]


class CompetitorNote(BaseModel):
    """Short explanation of what one competitor means for SCADABLE."""

    company_name: str
    why_it_matters: str


class SWOTAnalysis(BaseModel):
    strengths: list[str]
    weaknesses: list[str]
    opportunities: list[str]
    threats: list[str]
    competitor_notes: list[CompetitorNote]

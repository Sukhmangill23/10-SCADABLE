"""Initial structured contracts; fields will evolve with team requirements."""

from pydantic import BaseModel, Field

from models.crawl_result import ScrapedContent


class AnalysisInput(BaseModel):
    company_name: str = Field(min_length=1)
    pages: list[ScrapedContent]


class ExtractedInformation(BaseModel):
    """Facts extracted from source pages before interpretation."""

    company_name: str
    summary: str
    features: list[str]
    target_customers: list[str]
    # Plain strings keep LLM output schemas within OpenAI's supported formats.
    source_urls: list[str]


class CompanyAnalysis(BaseModel):
    """Shared analysis shape for a competitor or SCADABLE."""

    company_name: str
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    source_urls: list[str]


class ComparisonInput(BaseModel):
    scadable: CompanyAnalysis
    competitors: list[CompanyAnalysis]


class SWOTAnalysis(BaseModel):
    strengths: list[str]
    weaknesses: list[str]
    opportunities: list[str]
    threats: list[str]

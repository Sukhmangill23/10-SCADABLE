"""Initial structured contracts; fields will evolve with team requirements."""

from pydantic import BaseModel, Field

from models.crawl_result import ScrapedContent


class AnalysisInput(BaseModel):
    company_name: str = Field(min_length=1)
    pages: list[ScrapedContent]

class ClaimCited(BaseModel):
    """
    Claims extracted from the company with the links to cite them.
    """
    category: str
    claim: str
    source_url: str 

class ExtractedInformation(BaseModel):
    """Facts extracted from source pages before interpretation."""

    company_name: str
    summary: str
    features: list[str]
    target_customers: list[str]
    pricing: list[str]
    integrations: list[str]
    differentiators: list[str]
    # Plain strings keep LLM output schemas within OpenAI's supported formats.
    claims_cited: list[ClaimCited]  # Claims are the keys and links are the values.

class CompanyAnalysis(BaseModel):
    """Shared analysis shape for a competitor or SCADABLE."""

    company_name: str
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    # source_urls: list[str]
    claims_cited: list[ClaimCited]  # Claims are the keys and links are the values.


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

"""Initial structured contracts; fields will evolve with team requirements."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from models.crawl_result import ScrapedContent


class AnalysisInput(BaseModel):
    company_name: str = Field(min_length=1)
    pages: list[ScrapedContent]

Category = Literal[
    "summary",
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


class ExtractedInformation(BaseModel):
    """Facts extracted from source pages before interpretation."""

    company_name: str
    summary: str
    # Every fact is one cited claim; read them back by category with claims_in().
    claims_cited: list[ClaimCited]

    def claims_in(self, category: Category) -> list[str]:
        return [c.claim for c in self.claims_cited if c.category == category]


class CompanyAnalysis(BaseModel):
    """Shared analysis shape for a competitor or SCADABLE."""

    company_name: str
    summary: str
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

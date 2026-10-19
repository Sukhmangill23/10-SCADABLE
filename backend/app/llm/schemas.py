"""Structured contracts for each LLM stage.

Models used as ``output_schema`` must stay within OpenAI strict structured
output rules: every field required (no defaults), nullable via ``| None``,
and enums via ``Literal``.
"""

from typing import Literal

from pydantic import BaseModel, Field

FactTopic = Literal[
    "product",
    "frameworks",
    "integrations",
    "pricing",
    "target_customers",
    "automation",
    "ai_features",
    "auditor_network",
    "regulatory_coverage",
    "company",
    "other",
]

SignalDimension = Literal[
    "framework_coverage",
    "eu_regulation",
    "pricing",
    "developer_experience",
    "automation",
    "integrations",
    "auditor_network",
    "market_presence",
    "target_market",
    "other",
]

SWOTCategoryLiteral = Literal["strength", "weakness", "opportunity", "threat"]
EvidenceStatus = Literal["confirmed", "not_found"]


# ---------------------------------------------------------------------------
# Inputs (not sent as output schemas)
# ---------------------------------------------------------------------------


class PageInput(BaseModel):
    """One cleaned source page from the crawler (Person 1's contract)."""

    url: str
    title: str | None = None
    text: str = ""


class AnalysisInput(BaseModel):
    company_name: str = Field(min_length=1)
    pages: list[PageInput]


# ---------------------------------------------------------------------------
# Stage 1: fact extraction
# ---------------------------------------------------------------------------


class ExtractedFact(BaseModel):
    topic: FactTopic
    statement: str
    source_url: str
    evidence_quote: str


class ExtractedInformation(BaseModel):
    """Facts extracted from source pages before interpretation."""

    company_name: str
    summary: str
    frameworks: list[str]
    features: list[str]
    integrations: list[str]
    target_customers: list[str]
    pricing_summary: str | None
    facts: list[ExtractedFact]
    missing_topics: list[FactTopic]
    source_urls: list[str]


# ---------------------------------------------------------------------------
# Stage 2: SCADABLE baseline analysis
# ---------------------------------------------------------------------------


class CompanyAnalysis(BaseModel):
    """Shared analysis shape for a competitor or SCADABLE."""

    company_name: str
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    source_urls: list[str]


# ---------------------------------------------------------------------------
# Stage 3: comparison (profile + signals + SWOT)
# ---------------------------------------------------------------------------


class CompetitorProfile(BaseModel):
    company_name: str
    summary: str
    target_customers: list[str]
    frameworks: list[str]
    key_features: list[str]
    integrations: list[str]
    pricing_summary: str | None
    source_urls: list[str]


class CompetitiveSignal(BaseModel):
    dimension: SignalDimension
    competitor_position: str
    scadable_position: str
    advantage: Literal["scadable", "competitor", "parity", "unknown"]
    status: EvidenceStatus
    source_urls: list[str]


class SWOTFinding(BaseModel):
    category: SWOTCategoryLiteral
    content: str
    status: EvidenceStatus
    source_urls: list[str]


class ComparisonResult(BaseModel):
    profile: CompetitorProfile
    signals: list[CompetitiveSignal]
    swot: list[SWOTFinding]

"""Check the cited-claims schema helpers and constraints."""

import pytest
from pydantic import ValidationError

from llm.schemas import ClaimCited, CompanyAnalysis, ExtractedInformation


def claim(category, text, url="https://example.com/"):
    return ClaimCited(category=category, claim=text, source_url=url)


def test_company_analysis_exposes_strengths_and_weaknesses_from_claims():
    analysis = CompanyAnalysis(
        company_name="Acme",
        summary="s",
        claims_cited=[
            claim("strength", "Fast"),
            claim("weakness", "Pricey"),
            claim("strength", "Reliable"),
        ],    scores=[],
    )
    assert analysis.strengths == ["Fast", "Reliable"]
    assert analysis.weaknesses == ["Pricey"]


def test_extracted_information_filters_claims_by_category():
    facts = ExtractedInformation(
        company_name="Acme",
        summary="s",
        claims_cited=[claim("pricing", "Pro, $9"), claim("features", "Reports")],
    )
    assert facts.claims_in("pricing") == ["Pro, $9"]
    assert facts.claims_in("integrations") == []


def test_unknown_category_is_rejected():
    with pytest.raises(ValidationError):
        ClaimCited(category="opportunity", claim="x", source_url="https://example.com/")


def test_json_schema_restricts_category_to_known_values():
    schema = ClaimCited.model_json_schema()
    assert set(schema["properties"]["category"]["enum"]) == {
        "summary", "features", "target_customers", "pricing",
        "integrations", "differentiators", "strength", "weakness",
    }

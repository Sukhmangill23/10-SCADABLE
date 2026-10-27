"""Check the cited-claims schema helpers and constraints."""

import pytest
from pydantic import ValidationError

from llm.schemas import (
    ClaimCited,
    CompanyAnalysis,
    ExtractedInformation,
    FeatureScore,
    PartialCompanyAnalysis,
)


def claim(category, text, url="https://example.com/"):
    return ClaimCited(category=category, claim=text, source_url=url)


def test_company_analysis_exposes_strengths_and_weaknesses_from_claims():
    analysis = CompanyAnalysis(
        company_name="Acme",
        summary="s",
        summary_source_urls=["https://example.com/"],
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
        summary_source_urls=["https://example.com/"],
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
        "features", "target_customers", "pricing",
        "integrations", "differentiators", "strength", "weakness",
    }


def test_partial_analysis_schema_only_asks_the_model_for_new_data():
    # The schema sent to OpenAI must not contain the fields we copy in ourselves.
    schema = PartialCompanyAnalysis.model_json_schema()
    assert set(schema["properties"]) == {"claims_cited", "scores"}
    assert set(schema["required"]) == {"claims_cited", "scores"}


def test_full_analysis_schema_keeps_every_field():
    schema = CompanyAnalysis.model_json_schema()
    assert set(schema["properties"]) == {
        "company_name",
        "summary",
        "summary_source_urls",
        "claims_cited",
        "scores",
    }


def test_extracted_information_asks_the_model_for_summary_sources():
    schema = ExtractedInformation.model_json_schema()
    assert "summary_source_urls" in schema["required"]


def test_company_analysis_is_built_from_partial_plus_supplied_fields():
    partial = PartialCompanyAnalysis(
        claims_cited=[claim("strength", "Fast")],
        scores=[FeatureScore(feature="Reports", score=4)],
    )
    analysis = CompanyAnalysis(
        **partial.model_dump(),
        company_name="Acme",
        summary="Acme sells widgets",
        summary_source_urls=["https://example.com/"],
    )
    assert analysis.company_name == "Acme"
    assert analysis.summary_page_urls == ["https://example.com/"]
    assert analysis.strengths == ["Fast"]
    assert analysis.scores[0].feature == "Reports"


@pytest.mark.parametrize("missing", ["company_name", "summary", "summary_source_urls"])
def test_full_analysis_requires_the_copied_fields(missing):
    fields = {
        "company_name": "Acme",
        "summary": "s",
        "summary_source_urls": ["https://example.com/"],
        "claims_cited": [],
        "scores": [],
    }
    del fields[missing]
    with pytest.raises(ValidationError):
        CompanyAnalysis(**fields)


def test_full_analysis_rejects_null_name_and_summary():
    with pytest.raises(ValidationError):
        CompanyAnalysis(
            company_name=None,
            summary=None,
            summary_source_urls=[],
            claims_cited=[],
            scores=[],
        )

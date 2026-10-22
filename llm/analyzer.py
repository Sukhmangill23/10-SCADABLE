"""Structured analysis entry points with source-citation validation."""

from typing import Optional
from llm.client import OpenAIClient
from llm.prompts.comparison import (
    COMPARISON_SYSTEM_PROMPT,
    build_comparison_user_prompt,
)
from llm.prompts.competitor import (
    COMPANY_ANALYSIS_SYSTEM_PROMPT,
    DATA_EXTRACTION_SYSTEM_PROMPT,
    build_company_user_prompt,
    build_extraction_user_prompt,
)
from llm.schemas import (
    AnalysisInput,
    ClaimCited,
    PartialCompanyAnalysis,
    CompanyAnalysis,
    ComparisonInput,
    ExtractedInformation,
    SWOTAnalysis,
)


def _validate_citations(*, summary_source_urls: list[str] = [], claims: list[ClaimCited], source_urls: set[str]) -> None:
    for url in summary_source_urls:
        if url not in source_urls:
            raise ValueError(
                            f"A citation URL for the summary is not present in the supplied sources: {url}"
                        )
    for claim in claims:
        if claim.source_url not in source_urls:
            raise ValueError(
                f"Citation URL for a claim is not present in the supplied sources: {claim.source_url}"
            )


class Analyzer:
    def __init__(self, client: OpenAIClient) -> None:
        self.client = client

    # TODO: Make this return a "PartialExtractedInformation", fix the prompt for it too!
    async def extract_information(self, data: AnalysisInput) -> ExtractedInformation:
        result = await self.client.generate_structured(
            instructions=DATA_EXTRACTION_SYSTEM_PROMPT,
            input_text=build_extraction_user_prompt(data),
            output_schema=ExtractedInformation,
        )
        _validate_citations(
            summary_source_urls=result.summary_source_urls, claims=result.claims_cited, source_urls={str(page.source.url) for page in data.pages}
        )
        return result

    async def analyze_competitor(self, data: ExtractedInformation) -> CompanyAnalysis:
        partial_result = await self.client.generate_structured(
            instructions=COMPANY_ANALYSIS_SYSTEM_PROMPT,
            input_text=build_company_user_prompt(data),
            output_schema=PartialCompanyAnalysis,
        )
        _validate_citations(
            claims=partial_result.claims_cited, source_urls={claim.source_url for claim in data.claims_cited}
        )
        result = build_company_analysis(partial_result, data)
        return result

    async def analyze_scadable(self, data: ExtractedInformation) -> CompanyAnalysis:
        partial_result = await self.client.generate_structured(
            instructions=COMPANY_ANALYSIS_SYSTEM_PROMPT,
            input_text=build_company_user_prompt(data),
            output_schema=PartialCompanyAnalysis,
        )
        _validate_citations(
            claims=partial_result.claims_cited, source_urls={claim.source_url for claim in data.claims_cited}
        )
        result = build_company_analysis(partial_result, data)
        return result

    async def compare(self, data: ComparisonInput) -> SWOTAnalysis:
        return await self.client.generate_structured(
            instructions=COMPARISON_SYSTEM_PROMPT,
            input_text=build_comparison_user_prompt(data),
            output_schema=SWOTAnalysis,
        )
    
def build_company_analysis(partialresult: PartialCompanyAnalysis, data: ExtractedInformation) -> CompanyAnalysis:
    """
    A helper function that returns the partial result into a CompanyAnalysis object, 
    containing the company's name, summary, and source URLs for the summary.
    """
    return CompanyAnalysis(**partialresult.model_dump(), company_name=data.company_name, 
                           summary=data.summary, summary_source_urls=data.summary_source_urls)

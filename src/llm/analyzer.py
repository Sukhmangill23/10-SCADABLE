"""Structured analysis entry points with source-citation validation."""

from llm.client import OpenAIClient
from llm.prompts.comparison import (
    COMPARISON_SYSTEM_PROMPT,
    build_comparison_user_prompt,
)
from llm.prompts.competitor import (
    COMPANY_SYSTEM_PROMPT,
    EXTRACTION_SYSTEM_PROMPT,
    build_company_user_prompt,
    build_extraction_user_prompt,
)
from llm.schemas import (
    AnalysisInput,
    ClaimCited,
    CompanyAnalysis,
    ComparisonInput,
    ExtractedInformation,
    SWOTAnalysis,
)


def _validate_citations(claims: list[ClaimCited], source_urls: set[str]) -> None:
    for claim in claims:
        if claim.source_url not in source_urls:
            raise ValueError(
                f"Citation URL is not present in the supplied sources: {claim.source_url}"
            )


class Analyzer:
    def __init__(self, client: OpenAIClient) -> None:
        self.client = client

    async def extract_information(self, data: AnalysisInput) -> ExtractedInformation:
        result = await self.client.generate_structured(
            instructions=EXTRACTION_SYSTEM_PROMPT,
            input_text=build_extraction_user_prompt(data),
            output_schema=ExtractedInformation,
        )
        _validate_citations(
            result.claims_cited, {str(page.source.url) for page in data.pages}
        )
        return result

    async def analyze_competitor(self, data: ExtractedInformation) -> CompanyAnalysis:
        result = await self.client.generate_structured(
            instructions=COMPANY_SYSTEM_PROMPT,
            input_text=build_company_user_prompt(data),
            output_schema=CompanyAnalysis,
        )
        _validate_citations(
            result.claims_cited, {claim.source_url for claim in data.claims_cited}
        )
        return result

    async def analyze_scadable(self, data: ExtractedInformation) -> CompanyAnalysis:
        result = await self.client.generate_structured(
            instructions=COMPANY_SYSTEM_PROMPT,
            input_text=build_company_user_prompt(data),
            output_schema=CompanyAnalysis,
        )
        _validate_citations(
            result.claims_cited, {claim.source_url for claim in data.claims_cited}
        )
        return result

    async def compare(self, data: ComparisonInput) -> SWOTAnalysis:
        return await self.client.generate_structured(
            instructions=COMPARISON_SYSTEM_PROMPT,
            input_text=build_comparison_user_prompt(data),
            output_schema=SWOTAnalysis,
        )

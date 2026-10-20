"""Analysis entry points; business logic is intentionally unimplemented."""

from llm.client import OpenAIClient
from llm.schemas import (
    AnalysisInput,
    CompanyAnalysis,
    ComparisonInput,
    ExtractedInformation,
    SWOTAnalysis,
)
from llm.prompts.competitor import EXTRACTION_SYSTEM_PROMPT, COMPANY_SYSTEM_PROMPT, \
    build_extraction_user_prompt, build_company_user_prompt
from llm.prompts.comparison import COMPARISON_SYSTEM_PROMPT, build_comparison_user_prompt


class Analyzer:
    def __init__(self, client: OpenAIClient) -> None:
        self.client = client

    async def extract_information(self, data: AnalysisInput) -> ExtractedInformation:
        # TODO: Prepare source content and use EXTRACTION_PROMPT with the client.
        return await self.client.generate_structured(instructions=EXTRACTION_SYSTEM_PROMPT, 
                                            input_text=build_extraction_user_prompt(data), 
                                            output_schema=ExtractedInformation)

    async def analyze_competitor(self, data: ExtractedInformation) -> CompanyAnalysis:
        # TODO: Use COMPETITOR_PROMPT and return validated CompanyAnalysis.
        return await self.client.generate_structured(instructions=COMPANY_SYSTEM_PROMPT, 
                                               input_text=build_company_user_prompt(data), 
                                               output_schema=CompanyAnalysis)
        

    async def analyze_scadable(self, data: ExtractedInformation) -> CompanyAnalysis:
        # TODO: Use SCADABLE_PROMPT and return validated CompanyAnalysis.
        return await self.client.generate_structured(instructions=COMPANY_SYSTEM_PROMPT, 
                                               input_text=build_company_user_prompt(data), 
                                               output_schema=CompanyAnalysis)

    async def compare(self, data: ComparisonInput) -> SWOTAnalysis:
        # TODO: Use COMPARISON_PROMPT once comparison requirements are agreed.
        return await self.client.generate_structured(instructions=COMPARISON_SYSTEM_PROMPT, 
                                               input_text=build_comparison_user_prompt(data), 
                                               output_schema=SWOTAnalysis)

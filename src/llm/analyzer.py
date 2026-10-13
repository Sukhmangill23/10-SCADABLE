"""Analysis entry points; business logic is intentionally unimplemented."""

from llm.client import OpenAIClient
from llm.schemas import (
    AnalysisInput,
    CompanyAnalysis,
    ComparisonInput,
    ExtractedInformation,
    SWOTAnalysis,
)


class Analyzer:
    def __init__(self, client: OpenAIClient) -> None:
        self.client = client

    async def extract_information(self, data: AnalysisInput) -> ExtractedInformation:
        # TODO: Prepare source content and use EXTRACTION_PROMPT with the client.
        raise NotImplementedError("Information extraction is not implemented yet.")

    async def analyze_competitor(self, data: ExtractedInformation) -> CompanyAnalysis:
        # TODO: Use COMPETITOR_PROMPT and return validated CompanyAnalysis.
        raise NotImplementedError("Competitor analysis is not implemented yet.")

    async def analyze_scadable(self, data: ExtractedInformation) -> CompanyAnalysis:
        # TODO: Use SCADABLE_PROMPT and return validated CompanyAnalysis.
        raise NotImplementedError("SCADABLE analysis is not implemented yet.")

    async def compare(self, data: ComparisonInput) -> SWOTAnalysis:
        # TODO: Use COMPARISON_PROMPT once comparison requirements are agreed.
        raise NotImplementedError("Comparison and SWOT are not implemented yet.")

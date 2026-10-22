"""Enforce source citations at the boundary of structured model responses."""

import pytest

from llm.analyzer import Analyzer
from llm.inputs import load_analysis_input
from llm.schemas import ClaimCited, CompanyAnalysis, ExtractedInformation, PartialCompanyAnalysis
from tests.helpers import MARKDOWN, make_page, make_result, write_export

pytestmark = pytest.mark.asyncio


class ResponseClient:
    def __init__(self, response):
        self.response = response
        self.requests = []

    async def generate_structured(self, **request):
        self.requests.append(request)
        return self.response


def facts(source_url="https://example.com/"):
    return ExtractedInformation(
        company_name="Example",
        summary="Evidence collection",
        summary_source_urls=[source_url],
        claims_cited=[
            ClaimCited(
                category="features", claim="Collects evidence", source_url=source_url
            )
        ],
    )


def analysis(source_url="https://example.com/"):
    return CompanyAnalysis(
        company_name="Example",
        summary="Evidence collection",
        summary_source_urls=[source_url],
        claims_cited=[
            ClaimCited(
                category="strength", claim="Collects evidence", source_url=source_url
            )
        ],
        scores=[],
    )


def partial(source_url="https://example.com/"):
    return PartialCompanyAnalysis(
        claims_cited=[ClaimCited(category="strength", claim="Collects evidence", source_url=source_url)],
        scores=[],
    )

@pytest.mark.parametrize("method", ["analyze_competitor", "analyze_scadable"])
async def test_company_analysis_rejects_citations_not_present_in_facts(method):
    analyzer = Analyzer(ResponseClient(analysis("https://invented.example/")))

    with pytest.raises(ValueError, match="not present in the supplied sources"):
        await getattr(analyzer, method)(facts())

@pytest.mark.parametrize("method", ["analyze_competitor", "analyze_scadable"])
async def test_company_analysis_adds_name_and_summary_from_facts(method):
    client = ResponseClient(partial())
    result = await getattr(Analyzer(client), method)(facts())

    assert result.company_name == "Example"                 # from facts, not the model
    assert result.summary == "Evidence collection"
    assert result.claims_cited == partial().claims_cited
    assert client.requests[0]["output_schema"] is PartialCompanyAnalysis


@pytest.mark.parametrize(
    "citation", ["https://invented.example/", "https://example.com/new/"]
)
async def test_extraction_rejects_urls_other_than_original_source(tmp_path, citation):
    index = write_export(
        tmp_path, make_result(pages=[make_page(final_url="https://example.com/new/")])
    )
    analyzer = Analyzer(ResponseClient(facts(citation)))

    with pytest.raises(ValueError, match="not present in the supplied sources"):
        await analyzer.extract_information(load_analysis_input(index))


async def test_extraction_supplies_markdown_and_source_metadata(tmp_path):
    index = write_export(
        tmp_path, make_result(pages=[make_page(final_url="https://example.com/new/")])
    )
    client = ResponseClient(facts())
    result = await Analyzer(client).extract_information(load_analysis_input(index))

    assert result.claims_cited[0].source_url == "https://example.com/"
    prompt = client.requests[0]["input_text"]
    assert MARKDOWN in prompt
    assert "https://example.com/" in prompt and "https://example.com/new/" in prompt
    assert "Example home" in prompt and "features" in prompt
    assert "2026-10-19T12:00:00+00:00" in prompt

async def test_extraction_rejects_summary_urls_not_in_the_input_pages(tmp_path):
    index = write_export(tmp_path, make_result(pages=[make_page()]))
    bad = facts().model_copy(update={"summary_source_urls": ["https://invented.example/"]})
    analyzer = Analyzer(ResponseClient(bad))

    with pytest.raises(ValueError, match="summary is not present"):
        await analyzer.extract_information(load_analysis_input(index))

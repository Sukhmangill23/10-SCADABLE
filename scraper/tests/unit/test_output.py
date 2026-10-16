import io
import json

from scadable_scraper import CompetitorCrawlResult, ScrapedPage
from scadable_scraper.types import utc_now


def crawl_result():
    now = utc_now()
    return CompetitorCrawlResult(
        competitor_name="Exämple",
        homepage_url="https://example.com",
        started_at=now,
        finished_at=now,
        run_status="success",
        completion_reason="completed",
        pages=[
            ScrapedPage(
                competitor_name="Exämple",
                homepage_url="https://example.com",
                source_url="https://example.com/pricing",
                crawl_timestamp=now,
                crawl_status="success",
                raw_markdown="€49",
                cleaned_markdown="€49",
            )
        ],
    )


def test_json_run_document_round_trip():
    from scadable_scraper.models import CrawlRunDocument
    from scadable_scraper.output import write_json

    result = crawl_result()
    document = CrawlRunDocument(results=[result])
    stream = io.StringIO()
    write_json(document, stream)
    parsed = CrawlRunDocument.model_validate_json(stream.getvalue())
    assert parsed.results == [result]
    assert parsed.schema_version == "1.0"
    assert "€49" in stream.getvalue()


async def test_jsonl_records_reconstruct_result_without_repeating_page_bodies():
    from scadable_scraper.output import JsonlSink, parse_jsonl_record

    result = crawl_result()
    stream = io.StringIO()
    sink = JsonlSink(stream)
    for page in result.pages:
        await sink.write_page(page)
    await sink.write_summary(result)
    lines = stream.getvalue().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["record_type"] == "page"
    summary = json.loads(lines[1])
    assert summary["record_type"] == "competitor_summary"
    assert "pages" not in summary["result"]
    records = [parse_jsonl_record(line) for line in lines]
    reconstructed = CompetitorCrawlResult.model_validate(
        records[1].result.model_dump() | {"pages": [records[0].page]}
    )
    assert reconstructed == result

"""Typed UTF-8 JSON/JSONL serialization, independent of browser and service ownership."""

from typing import Annotated, TextIO

from pydantic import Field, TypeAdapter

from .models import (
    CompetitorCrawlResult,
    CompetitorSummary,
    CompetitorSummaryRecord,
    CrawlRunDocument,
    PageRecord,
    ScrapedPage,
)

JsonlRecord = Annotated[PageRecord | CompetitorSummaryRecord, Field(discriminator="record_type")]
_RECORD_ADAPTER = TypeAdapter(JsonlRecord)


def parse_jsonl_record(line: str) -> PageRecord | CompetitorSummaryRecord:
    return _RECORD_ADAPTER.validate_json(line)


def write_json(document: CrawlRunDocument, stream: TextIO) -> None:
    stream.write(document.model_dump_json(indent=2) + "\n")
    stream.flush()


class JsonlSink:
    """Caller owns the stream. A summary follows its pages; completed competitors flush."""

    def __init__(self, stream: TextIO):
        self.stream = stream

    async def write_page(self, page: ScrapedPage) -> None:
        self.stream.write(PageRecord(page=page).model_dump_json() + "\n")

    async def write_summary(self, result: CompetitorCrawlResult) -> None:
        summary = CompetitorSummary.model_validate(result.model_dump(exclude={"pages"}))
        self.stream.write(CompetitorSummaryRecord(result=summary).model_dump_json() + "\n")
        self.stream.flush()

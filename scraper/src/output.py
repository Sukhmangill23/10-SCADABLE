"""Typed UTF-8 JSON/JSONL serialization, independent of browser and service ownership."""

import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
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


@contextmanager
def atomic_json_file(path: Path, *, overwrite: bool = False):
    """Publish a completed UTF-8 JSON file on the same filesystem, without early truncation."""
    if not overwrite and (path.exists() or path.is_symlink()):
        raise FileExistsError(f"Output exists: {path}; use --overwrite to replace it")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temporary_path = Path(temporary.name)
    try:
        with temporary as stream:
            yield stream
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(temporary_path, path)
        else:
            # Atomic no-overwrite publication; never replace a file created during crawl.
            os.link(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


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

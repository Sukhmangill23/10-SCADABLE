"""Verify the scraper-export reader against a fake run folder on disk."""

import asyncio
import json

import pytest

from crawling.exporteddatacrawler import ExportedDataCrawler
from models.crawl_result import CompetitorURL


def write_export(run_dir, host, pages):
    """Create <run_dir>/<host>/ with crawl_summary.json and one .md file per page."""
    folder = run_dir / host
    entries = []
    for page in pages:
        entry = {
            "url": page["url"],
            "title": page.get("title"),
            "status": page.get("status", "success"),
        }
        if "text" in page:
            md_path = folder / page["file"]
            md_path.parent.mkdir(parents=True, exist_ok=True)
            md_path.write_text(page["text"], encoding="utf-8")
            entry["markdown_file"] = page["file"]
        entries.append(entry)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "crawl_summary.json").write_text(
        json.dumps({"pages": entries}), encoding="utf-8"
    )


def crawl(run_dir, name, url):
    crawler = ExportedDataCrawler(run_dir)
    return asyncio.run(crawler.crawl(CompetitorURL(name=name, url=url)))


def test_returns_successful_pages_with_text_and_metadata(tmp_path):
    write_export(
        tmp_path,
        "cluely.com",
        [
            {"url": "https://cluely.com/", "title": "Home", "file": "pages/index.md",
             "text": "# Cluely\n\nAI meeting assistant"},
            {"url": "https://cluely.com/pricing", "title": "Pricing",
             "file": "pages/pricing.md", "text": "Pro: $11.99/mo"},
        ],
    )
    result = crawl(tmp_path, "Cluely", "https://cluely.com")
    assert result.provider == "crawl4ai"
    assert result.competitor.name == "Cluely"
    assert [str(p.url) for p in result.pages] == [
        "https://cluely.com/",
        "https://cluely.com/pricing",
    ]
    assert result.pages[0].title == "Home"
    assert result.pages[0].text == "# Cluely\n\nAI meeting assistant"


def test_skips_failed_pages_without_markdown_files(tmp_path):
    write_export(
        tmp_path,
        "cluely.com",
        [
            {"url": "https://cluely.com/", "title": "Home", "file": "pages/index.md",
             "text": "ok"},
            {"url": "https://cluely.com/broken", "status": "failed"},
        ],
    )
    result = crawl(tmp_path, "Cluely", "https://cluely.com")
    assert [str(p.url) for p in result.pages] == ["https://cluely.com/"]


def test_reads_the_folder_matching_the_competitor_host(tmp_path):
    write_export(tmp_path, "cluely.com", [
        {"url": "https://cluely.com/", "file": "pages/index.md", "text": "cluely"}])
    write_export(tmp_path, "www.bluej.com", [
        {"url": "https://www.bluej.com/", "file": "pages/index.md", "text": "blue j"}])
    result = crawl(tmp_path, "Blue J", "https://www.bluej.com")
    assert [p.text for p in result.pages] == ["blue j"]


def test_reads_nested_markdown_paths_and_unicode(tmp_path):
    write_export(tmp_path, "scadable.com", [
        {"url": "https://scadable.com/blog/post", "title": "Post",
         "file": "pages/blog/post.md", "text": "Café — “quoted” text"}])
    result = crawl(tmp_path, "SCADABLE", "https://scadable.com")
    assert result.pages[0].text == "Café — “quoted” text"


def test_missing_title_is_allowed(tmp_path):
    write_export(tmp_path, "cluely.com", [
        {"url": "https://cluely.com/", "file": "pages/index.md", "text": "ok"}])
    result = crawl(tmp_path, "Cluely", "https://cluely.com")
    assert result.pages[0].title is None


def test_export_with_no_successful_pages_returns_empty_list(tmp_path):
    write_export(tmp_path, "cluely.com", [
        {"url": "https://cluely.com/", "status": "failed"}])
    assert crawl(tmp_path, "Cluely", "https://cluely.com").pages == []


def test_missing_folder_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="cluely.com"):
        crawl(tmp_path, "Cluely", "https://cluely.com")


def test_folder_without_summary_is_treated_as_incomplete(tmp_path):
    (tmp_path / "cluely.com" / "pages").mkdir(parents=True)
    (tmp_path / "cluely.com" / "pages" / "index.md").write_text("x", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        crawl(tmp_path, "Cluely", "https://cluely.com")

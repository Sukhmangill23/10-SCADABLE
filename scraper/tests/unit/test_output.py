import json
from datetime import UTC, datetime, timedelta
from pathlib import Path, PureWindowsPath

import pytest
from pydantic import ValidationError

from scraper import CompetitorCrawlResult, ScrapedPage
from scraper.models import DiscoveredUrl, DiscoveryEvidence

NOW = datetime(2026, 10, 16, 14, tzinfo=UTC)


def page(url="https://example.com/pricing", **changes):
    return ScrapedPage(
        **{
            "competitor_name": "Example",
            "homepage_url": "https://example.com/",
            "source_url": url,
            "crawl_timestamp": NOW,
            "crawl_status": "success",
            "page_title": "Pricing",
            "page_category": "pricing",
            "raw_markdown": "# Raw source\n\nFull source remains in the Python API.",
            "cleaned_markdown": "# Plans\n\nPro costs €49 monthly.\n",
            **changes,
        }
    )


def result(pages=None, **changes):
    return CompetitorCrawlResult(
        **{
            "competitor_name": "Example",
            "homepage_url": "https://example.com/",
            "started_at": NOW,
            "finished_at": NOW + timedelta(seconds=10),
            "run_status": "success",
            "completion_reason": "completed",
            "pages": [page()] if pages is None else pages,
            **changes,
        }
    )


def test_export_separates_exact_cleaned_content_from_validated_summary(tmp_path):
    from scraper.models import CrawlExportSummary
    from scraper.output import export_competitor

    source = result()
    summary = export_competitor(source, tmp_path)
    folder = tmp_path / "example.com"
    assert (folder / "pages/pricing.md").read_text(encoding="utf-8") == source.pages[
        0
    ].cleaned_markdown
    text = (folder / "crawl_summary.json").read_text(encoding="utf-8")
    payload = json.loads(text)
    assert CrawlExportSummary.model_validate_json(text) == summary
    assert payload["schema_version"] == "2.0"
    assert payload["duration_seconds"] == 10.0
    assert payload["counts"]["successful"] == payload["counts"]["discovered"] == 1
    assert payload["pages"][0]["markdown_file"] == "pages/pricing.md"
    assert payload["pages"][0]["word_count"] == 5
    assert payload["pages"][0]["crawled_at"] == "2026-10-16T14:00:00Z"
    assert "raw_markdown" not in text and "cleaned_markdown" not in text
    assert "Full source" not in text and "€49" not in text
    assert "effective_config" not in payload and "metadata" not in payload["pages"][0]
    assert "duration_seconds" not in payload["pages"][0]


@pytest.mark.parametrize(
    "url,relative",
    [
        ("https://example.com/", "pages/index.md"),
        ("https://example.com/pricing", "pages/pricing.md"),
        ("https://example.com/pricing/", "pages/pricing/index.md"),
        ("https://example.com/products/analytics", "pages/products/analytics.md"),
    ],
)
def test_url_hierarchy_maps_to_readable_markdown_files(tmp_path, url, relative):
    from scraper.output import export_competitor

    summary = export_competitor(result([page(url)]), tmp_path)
    assert summary.pages[0].markdown_file == relative
    assert (tmp_path / "example.com" / relative).is_file()


def test_query_case_reserved_names_and_file_directory_conflicts_do_not_collide(tmp_path):
    from scraper.output import export_competitor

    paths = [
        "/",
        "/index",
        "/pricing",
        "/pricing/",
        "/pricing?currency=cad",
        "/pricing?currency=usd",
        "/Pricing",
        "/CON",
        "/con.txt",
        "/COM¹.old",
        "/LPT²",
        "/a%3Ab",
        "/a_b",
        "/a.md/child",
        "/a",
        "/a//child",
        "/a/child",
        "/%2Fescape",
        "/" + "/".join(["long-segment" * 5] * 12),
    ]
    pages = [
        page("https://example.com" + path, cleaned_markdown=f"Content {i}")
        for i, path in enumerate(paths)
    ]
    first = export_competitor(result(pages), tmp_path / "one")
    second = export_competitor(result(list(reversed(pages))), tmp_path / "two")
    mapping = {str(item.url): item.markdown_file for item in first.pages}
    assert mapping == {str(item.url): item.markdown_file for item in second.pages}
    assert len({value.casefold() for value in mapping.values()}) == len(paths)
    for source in pages:
        relative = mapping[str(source.source_url)]
        target = tmp_path / "one/example.com" / relative
        assert target.read_text(encoding="utf-8") == source.cleaned_markdown
        assert target.resolve().is_relative_to((tmp_path / "one/example.com/pages").resolve())
        assert "\\" not in relative and ":" not in relative
        assert not any(PureWindowsPath(part).is_reserved() for part in Path(relative).parts)
        assert len(relative) <= 160


def test_relationships_uncrawled_reasons_and_failure_details_are_preserved(tmp_path):
    from scraper.output import export_competitor

    pricing = page(metadata={"crawl_diagnostics": {"duration_seconds": 2.5}})
    failed = page(
        "https://example.com/faq", crawl_status="failed", error_message="Timeout", http_status=503
    )
    records = [
        DiscoveredUrl(
            url=pricing.source_url,
            normalized_url=pricing.source_url,
            discovery_source="sitemap",
            parent_url="https://example.com/sitemap.xml",
            disposition="crawled",
            depth=1,
            depth_basis="sitemap_seed",
            evidence=[
                DiscoveryEvidence(
                    observed_url=str(pricing.source_url),
                    discovery_source="internal_link",
                    parent_url="https://example.com/",
                    depth=1,
                ),
                DiscoveryEvidence(
                    observed_url=str(pricing.source_url),
                    discovery_source="internal_link",
                    parent_url="https://example.com/about",
                    depth=2,
                ),
            ],
        ),
        DiscoveredUrl(
            url=failed.source_url,
            normalized_url=failed.source_url,
            discovery_source="internal_link",
            disposition="failed",
            depth=2,
        ),
        DiscoveredUrl(
            url="https://example.com/blog",
            normalized_url="https://example.com/blog",
            discovery_source="internal_link",
            disposition="deferred",
            reason="page_limit",
            depth=1,
            parent_url="https://example.com/",
        ),
        DiscoveredUrl(
            url="https://example.com/login",
            normalized_url="https://example.com/login",
            discovery_source="internal_link",
            disposition="skipped",
            reason="excluded_pattern",
            depth=1,
        ),
        DiscoveredUrl(
            url="https://jobs.example.org/",
            normalized_url="https://jobs.example.org/",
            discovery_source="external_link",
            disposition="external",
            reason="domain_not_approved",
        ),
    ]
    summary = export_competitor(
        result(
            [pricing, failed],
            discovered_urls=records,
            run_status="partial",
            completion_reason="page_limit",
        ),
        tmp_path,
    )
    assert summary.counts.successful == summary.counts.failed == 1
    assert summary.counts.discovered == 5
    assert summary.counts.deferred == summary.counts.skipped == summary.counts.external == 1
    item = summary.pages[0]
    assert item.depth == 1 and item.depth_basis == "sitemap_seed"
    assert item.duration_seconds == 2.5
    assert set(item.discovery_sources) == {"sitemap", "internal_link"}
    assert {str(url) for url in item.discovered_from} == {
        "https://example.com/sitemap.xml",
        "https://example.com/",
        "https://example.com/about",
    }
    assert summary.pages[1].markdown_file is None
    assert summary.pages[1].error == "Timeout" and summary.pages[1].http_status == 503
    assert not (tmp_path / "example.com/pages/faq.md").exists()
    assert summary.uncrawled_urls[0].reason == "page_limit"


def test_existing_export_and_unrelated_files_are_preserved(tmp_path):
    from scraper.output import export_competitor

    target = tmp_path / "example.com"
    target.mkdir()
    notes = target / "notes.txt"
    notes.write_text("user notes", encoding="utf-8")
    with pytest.raises(FileExistsError):
        export_competitor(result(), tmp_path)
    assert notes.read_text(encoding="utf-8") == "user notes"
    assert list(target.iterdir()) == [notes]


def test_write_failure_does_not_publish_or_remove_other_data(tmp_path, monkeypatch):
    from scraper.output import export_competitor

    unrelated = tmp_path / "old.json"
    unrelated.write_text("old data", encoding="utf-8")
    original = Path.write_text

    def fail(path, *args, **kwargs):
        if path.suffix == ".md":
            raise OSError("disk full")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail)
    with pytest.raises(OSError, match="disk full"):
        export_competitor(result(), tmp_path)
    assert list(tmp_path.iterdir()) == [unrelated]


def test_directory_created_during_export_is_not_replaced(tmp_path, monkeypatch):
    from scraper.output import export_competitor

    original = Path.write_text

    def race(path, *args, **kwargs):
        if path.name == "crawl_summary.json":
            target = tmp_path / "example.com"
            target.mkdir()
            original(target / "notes.txt", "created concurrently", encoding="utf-8")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", race)
    with pytest.raises(FileExistsError):
        export_competitor(result(), tmp_path)
    assert (tmp_path / "example.com/notes.txt").read_text() == "created concurrently"
    assert list(tmp_path.iterdir()) == [tmp_path / "example.com"]


def test_duplicate_logical_page_urls_are_rejected_before_writing(tmp_path):
    from scraper.output import export_competitor

    with pytest.raises(ValueError, match="Duplicate"):
        export_competitor(result([page(), page("https://example.com/pricing#same")]), tmp_path)
    assert not list(tmp_path.iterdir())


def test_different_homepage_origins_get_separate_folders(tmp_path):
    from scraper.output import competitor_directory, export_competitor

    homepages = [
        "https://example.com/",
        "http://example.com/",
        "https://example.com:8443/",
        "https://www.example.com/",
    ]
    assert len({competitor_directory(url).casefold() for url in homepages}) == 4
    for homepage in homepages:
        export_competitor(result([], homepage_url=homepage), tmp_path)
        assert (tmp_path / competitor_directory(homepage) / "crawl_summary.json").is_file()


def test_secondary_host_directory_cannot_overlap_a_main_site_markdown_file(tmp_path):
    from scraper.output import export_competitor

    pages = [
        page("https://example.com/_hosts/other", cleaned_markdown="Main site"),
        page("https://other.md/", cleaned_markdown="Approved secondary host"),
    ]
    summary = export_competitor(result(pages), tmp_path)
    for source, item in zip(pages, summary.pages, strict=True):
        assert (
            tmp_path / "example.com" / item.markdown_file
        ).read_text() == source.cleaned_markdown


def test_interruption_during_staging_does_not_publish_a_summary(tmp_path, monkeypatch):
    from scraper.output import export_competitor

    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(Path, "write_text", interrupted)
    with pytest.raises(KeyboardInterrupt):
        export_competitor(result(), tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_publication_failure_leaves_no_completion_marker(tmp_path, monkeypatch):
    from scraper import output

    original = output.os.rename

    def fail(source, target):
        if source.name == "crawl_summary.json":
            raise OSError("publication interrupted")
        return original(source, target)

    monkeypatch.setattr(output.os, "rename", fail)
    with pytest.raises(OSError, match="publication interrupted"):
        output.export_competitor(result(), tmp_path)
    assert not (tmp_path / "example.com/crawl_summary.json").exists()
    assert (tmp_path / "example.com/pages/pricing.md").is_file()
    with pytest.raises(FileExistsError):
        output.export_competitor(result(), tmp_path)


def test_summary_rejects_counts_or_content_references_that_disagree(tmp_path):
    from scraper.models import CrawlExportSummary
    from scraper.output import export_competitor

    summary = export_competitor(result(), tmp_path)
    payload = summary.model_dump(mode="json")
    payload["counts"]["successful"] = 2
    with pytest.raises(ValidationError, match="Counts"):
        CrawlExportSummary.model_validate(payload)
    payload = summary.model_dump(mode="json")
    payload["pages"][0]["markdown_file"] = None
    with pytest.raises(ValidationError, match="Markdown file"):
        CrawlExportSummary.model_validate(payload)


def test_failure_error_compaction_never_drops_the_only_explanation(tmp_path):
    from scraper.output import export_competitor

    source = page(crawl_status="failed", error_message="Code context: unavailable")
    summary = export_competitor(result([source], run_status="failed"), tmp_path)
    assert summary.pages[0].error == "Code context: unavailable"


@pytest.mark.parametrize(
    "relative",
    [
        "../outside.md",
        "/absolute.md",
        "pages/../escape.md",
        "pages\\escape.md",
        "pages/C:/escape.md",
    ],
)
def test_summary_rejects_unsafe_markdown_references(relative):
    from scraper.models import ExportedPage

    with pytest.raises(ValidationError):
        ExportedPage(
            url="https://example.com/",
            url_path="/",
            markdown_file=relative,
            title="Home",
            category="positioning",
            word_count=1,
            status="success",
            crawled_at=NOW,
        )

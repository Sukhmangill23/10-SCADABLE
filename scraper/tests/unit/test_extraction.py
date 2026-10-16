import pytest

from scadable_scraper import CompetitorInput, FetchedPage, ScraperConfig
from scadable_scraper.types import utc_now


def fetched(**updates):
    values = dict(
        source_url="https://example.com/pricing",
        final_url="https://www.example.com/pricing",
        crawl_timestamp=utc_now(),
        crawl_status="success",
        http_status=200,
        raw_markdown="# Pricing\r\n\r\n| Plan | Price |\r\n|---|---|\r\n| Pro | $49 |\r\n",
        filtered_markdown="Pro: $49",
        metadata={"description": "Plans", "language": "en"},
    )
    return FetchedPage(**(values | updates))


def test_extract_preserves_sources_and_prices_while_normalizing_line_endings():
    from scadable_scraper.extraction import MarkdownExtractor

    source = fetched(page_title="Our plans")
    result = MarkdownExtractor().extract(
        source, CompetitorInput(homepage_url="https://example.com"), ScraperConfig()
    )
    assert result.raw_markdown == source.raw_markdown
    assert result.filtered_markdown == "Pro: $49"
    assert "| Pro | $49 |" in result.cleaned_markdown
    assert "\r" not in result.cleaned_markdown
    assert result.source_url == source.source_url
    assert result.final_url == source.final_url
    assert result.metadata == source.metadata
    assert result.page_category == "pricing"
    assert result.competitor_name == "example.com"


def test_cleaning_preserves_fenced_code_indentation_and_markdown_hard_breaks():
    from scadable_scraper.extraction import clean_markdown

    source = (
        "\x00# Features\r\nLine  \r\nnext\r\n\r\n"
        "```python\r\n    x = 1\r\n\r\n\r\n    y = 2\r\n```\r\n"
    )
    assert clean_markdown(source) == source.replace("\x00", "").replace("\r\n", "\n")


@pytest.mark.parametrize(
    "url,title,category",
    [
        ("/", "", "positioning"),
        ("/opaque", "Our integrations", "integrations"),
        ("/careers/jobs", "", "careers"),
        ("/blog/pricing", "", "pricing"),
        ("/opaque", "", "other"),
        ("/press-release/launch", "", "press_release"),
    ],
)
def test_category_uses_url_title_and_stable_specificity(url, title, category):
    from scadable_scraper.extraction import MarkdownExtractor

    result = MarkdownExtractor().extract(
        fetched(source_url="https://example.com" + url, final_url=None, page_title=title),
        CompetitorInput(homepage_url="https://example.com"),
        ScraperConfig(),
    )
    assert result.page_category == category


def test_empty_success_becomes_explicit_failure_and_partial_failed_content_survives():
    from scadable_scraper.extraction import MarkdownExtractor

    extractor = MarkdownExtractor()
    competitor = CompetitorInput(homepage_url="https://example.com")
    empty = extractor.extract(fetched(raw_markdown="  "), competitor, ScraperConfig())
    assert empty.crawl_status == "failed"
    assert empty.error_message == "empty_markdown"
    partial = extractor.extract(
        fetched(crawl_status="failed", error_message="timeout"), competitor, ScraperConfig()
    )
    assert partial.crawl_status == "failed"
    assert "$49" in partial.cleaned_markdown

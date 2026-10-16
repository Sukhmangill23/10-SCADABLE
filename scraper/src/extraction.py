"""Conservative, network-free extraction from application-owned fetched pages."""

import re
from urllib.parse import unquote, urlsplit

from .config import CompetitorInput, ScraperConfig
from .models import FetchedPage, ScrapedPage
from .types import CrawlStatus, PageCategory


def clean_markdown(markdown: str) -> str:
    """Normalize line endings and remove unsafe controls without reflowing Markdown.

    Keep indentation, repeated blank lines, tables, code and two-space hard breaks.
    Filtering is a separate, potentially lossy representation, never the source here.
    """
    return re.sub(
        r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", markdown.replace("\r\n", "\n").replace("\r", "\n")
    )


def categorize(page: FetchedPage, settings: ScraperConfig) -> PageCategory:
    from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer

    parts = urlsplit(str(page.final_url or page.source_url))
    text = unquote(parts.path + ("?" + parts.query if parts.query else ""))
    best, highest = PageCategory.OTHER, 0.0
    # Enum order is the documented tie-breaker, independent of TOML map ordering.
    for category in PageCategory:
        keywords = settings.category_keywords.get(category, [])
        if not keywords:
            continue
        scorer = KeywordRelevanceScorer(keywords=list(dict.fromkeys(w.lower() for w in keywords)))
        score = settings.url_keyword_weight * scorer.score(text)
        score += settings.title_keyword_weight * scorer.score(page.page_title or "")
        if score > highest:
            best, highest = category, score
    if highest == 0 and parts.path in ("", "/"):
        return PageCategory.POSITIONING
    return best


class MarkdownExtractor:
    def extract(
        self, page: FetchedPage, competitor: CompetitorInput, settings: ScraperConfig
    ) -> ScrapedPage:
        content = page.model_dump(exclude={"raw_html", "links"})
        if page.crawl_status == CrawlStatus.SUCCESS and not page.raw_markdown.strip():
            content.update(crawl_status=CrawlStatus.FAILED, error_message="empty_markdown")
        return ScrapedPage(
            **content,
            competitor_name=competitor.display_name,
            homepage_url=competitor.homepage_url,
            page_category=categorize(page, settings),
            cleaned_markdown=clean_markdown(page.raw_markdown),
        )

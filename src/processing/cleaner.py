"""Content preparation placeholder, independent of crawlers and the LLM."""

from models.crawl_result import ScrapedContent


def clean_content(content: ScrapedContent) -> ScrapedContent:
    """Prepare one page for analysis while preserving its source URL."""
    # We are keeping the markdown text for easier processing for the LLM
    return content.model_copy(update={"text": content.text.strip()})
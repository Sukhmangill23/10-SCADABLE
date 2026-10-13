"""Content preparation placeholder, independent of crawlers and the LLM."""

from models.crawl_result import ScrapedContent


def clean_content(content: ScrapedContent) -> ScrapedContent:
    """Prepare one page for analysis while preserving its source URL."""
    # TODO: Normalize whitespace and remove irrelevant page content.
    # TODO: Agree on HTML/markdown handling and preserve useful evidence.
    raise NotImplementedError("Content cleaning is not implemented yet.")

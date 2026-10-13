"""Data exchanged between crawlers and downstream processing."""

from pydantic import BaseModel, Field, HttpUrl

from config import CrawlerProvider


class CompetitorURL(BaseModel):
    """A competitor and the starting URL for its research run."""

    name: str = Field(min_length=1)
    url: HttpUrl


class ScrapedContent(BaseModel):
    """One source page, with text or markdown normalized by the adapter."""

    url: HttpUrl
    title: str | None = None
    text: str


class CrawlResult(BaseModel):
    """Provider-independent output for one competitor."""

    competitor: CompetitorURL
    provider: CrawlerProvider
    pages: list[ScrapedContent] = Field(default_factory=list)

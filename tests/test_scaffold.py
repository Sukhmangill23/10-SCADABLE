"""Verify public contracts and wiring without invoking external services."""

import asyncio

import pytest
from pydantic import ValidationError

from config import Settings
from crawling.base import BaseCrawler
from crawling.crawl4ai import Crawl4AICrawler
from crawling.firecrawl import FirecrawlCrawler
from crawling.manager import create_crawler
from llm.client import OpenAIClient
from models.crawl_result import CompetitorURL, CrawlResult


@pytest.mark.parametrize(
    ("provider", "crawler_type"),
    [("firecrawl", FirecrawlCrawler), ("crawl4ai", Crawl4AICrawler)],
)
def test_provider_selection_and_placeholder(provider, crawler_type):
    crawler = create_crawler(Settings(crawler_provider=provider, _env_file=None))
    assert isinstance(crawler, crawler_type)
    competitor = CompetitorURL(name="Example", url="https://example.com")
    with pytest.raises(NotImplementedError):
        asyncio.run(crawler.crawl(competitor))


def test_crawler_contract_is_abstract():
    with pytest.raises(TypeError):
        BaseCrawler()


def test_settings_load_dotenv_and_environment_override(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("CRAWLER_PROVIDER=firecrawl\n", encoding="utf-8")
    monkeypatch.delenv("CRAWLER_PROVIDER", raising=False)
    assert Settings(_env_file=env_file).crawler_provider == "firecrawl"
    monkeypatch.setenv("CRAWLER_PROVIDER", "crawl4ai")
    assert Settings(_env_file=env_file).crawler_provider == "crawl4ai"


def test_unknown_provider_is_rejected():
    with pytest.raises(ValidationError):
        Settings(crawler_provider="unknown", _env_file=None)


@pytest.mark.parametrize("url", ["not-a-url", "ftp://example.com"])
def test_competitor_requires_http_url(url):
    with pytest.raises(ValidationError):
        CompetitorURL(name="Example", url=url)


def test_crawl_result_round_trip_and_independent_page_lists():
    competitor = CompetitorURL(name="Example", url="https://example.com")
    first = CrawlResult(competitor=competitor, provider="firecrawl")
    second = CrawlResult(competitor=competitor, provider="firecrawl")
    assert first.pages is not second.pages
    assert CrawlResult.model_validate_json(first.model_dump_json()) == first


@pytest.mark.parametrize("api_key", [None, "", "   "])
def test_openai_requires_nonempty_key(api_key):
    settings = Settings(openai_api_key=api_key, openai_model="test", _env_file=None)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OpenAIClient(settings)


def test_openai_requires_model():
    settings = Settings(openai_api_key="test", openai_model="", _env_file=None)
    with pytest.raises(ValueError, match="OPENAI_MODEL"):
        OpenAIClient(settings)

"""Environment configuration; importing this module has no side effects."""

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

CrawlerProvider = Literal["firecrawl", "crawl4ai"]


class Settings(BaseSettings):
    """Read environment variables and an optional .env in the working directory."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    crawler_provider: CrawlerProvider = "firecrawl"
    firecrawl_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    openai_model: str = ""
    openai_timeout_seconds: float = Field(default=30.0, gt=0)

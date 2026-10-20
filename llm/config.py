"""Downstream analysis settings, separate from the scraper's collection policy."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Read environment variables and an optional .env in the working directory."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    openai_api_key: SecretStr | None = None
    openai_model: str = ""
    openai_timeout_seconds: float = Field(default=30.0, gt=0)

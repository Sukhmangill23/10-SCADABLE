"""LLM environment configuration; importing this module has no side effects."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """Read LLM settings from environment variables and an optional ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # Blank entries copied from .env.example mean "unset", not "".
        env_ignore_empty=True,
    )

    openai_api_key: SecretStr | None = None
    openai_model: str = ""
    openai_timeout_seconds: float = Field(default=40.0, gt=0)

    # USD per 1M tokens. Left unset, cost is reported as null rather than guessed.
    llm_price_input_per_1m: float | None = Field(default=None, ge=0)
    llm_price_output_per_1m: float | None = Field(default=None, ge=0)
    # Refuse a run whose estimated cost exceeds this (protects the API budget).
    llm_max_cost_per_run_usd: float | None = Field(default=None, gt=0)

    # Fall back to mock analysis when no API key/model is configured.
    # Set LLM_ALLOW_MOCK=false in production so misconfiguration fails loudly.
    llm_allow_mock: bool = True

    # Input trimming keeps latency and token cost bounded.
    llm_max_chars_per_page: int = Field(default=6000, gt=0)
    llm_max_total_chars: int = Field(default=40000, gt=0)

    def is_configured(self) -> bool:
        """Return True when a real OpenAI call can be attempted."""
        key = self.openai_api_key
        return bool(key and key.get_secret_value().strip() and self.openai_model.strip())

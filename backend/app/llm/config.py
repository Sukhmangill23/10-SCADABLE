"""LLM environment configuration; importing this module has no side effects."""

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """Read LLM settings from environment variables and an optional ``.env``.

    Model prices live in ``app.llm.pricing.PRICE_TABLE``, not in env.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # Blank entries copied from .env.example mean "unset", not "".
        env_ignore_empty=True,
        populate_by_name=True,
    )

    openai_api_key: SecretStr | None = None
    openai_model: str = ""
    openai_timeout_seconds: float = Field(default=40.0, gt=0)

    # Abort a run when its estimated cost would pass this cap (safety net;
    # a typical run costs about $0.01).
    max_run_cost_usd: float = Field(
        default=0.25, gt=0, validation_alias=AliasChoices("MAX_RUN_COST_USD", "max_run_cost_usd")
    )
    # Total LLM budget for the whole project.
    project_budget_usd: float = Field(
        default=100.0,
        gt=0,
        validation_alias=AliasChoices("PROJECT_BUDGET_USD", "project_budget_usd"),
    )

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

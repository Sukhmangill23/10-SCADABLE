"""Small reusable wrapper around the OpenAI Responses API."""

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.llm.config import LLMSettings

OutputModel = TypeVar("OutputModel", bound=BaseModel)


@dataclass
class StructuredResult(Generic[OutputModel]):
    """Parsed model output plus the token usage reported by the API."""

    output: OutputModel
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0


class LLMClientProtocol(Protocol):
    """Interface the analyzer needs; tests substitute a fake implementation."""

    model: str

    async def generate_structured(
        self,
        *,
        instructions: str,
        input_text: str,
        output_schema: type[OutputModel],
        cache_key: str | None = None,
    ) -> StructuredResult[OutputModel]: ...

    async def close(self) -> None: ...


class OpenAIClient:
    """Own one async SDK client; callers must close it after use."""

    def __init__(self, settings: LLMSettings) -> None:
        api_key = settings.openai_api_key
        if api_key is None or not api_key.get_secret_value().strip():
            raise ValueError("Set OPENAI_API_KEY before constructing OpenAIClient.")
        if not settings.openai_model.strip():
            raise ValueError("Set OPENAI_MODEL before constructing OpenAIClient.")
        self.model = settings.openai_model.strip()
        self.sdk = AsyncOpenAI(
            api_key=api_key.get_secret_value(),
            timeout=settings.openai_timeout_seconds,
        )

    async def generate_structured(
        self,
        *,
        instructions: str,
        input_text: str,
        output_schema: type[OutputModel],
        cache_key: str | None = None,
    ) -> StructuredResult[OutputModel]:
        """Send an explicit request and parse its output into a Pydantic model.

        ``cache_key`` is forwarded as OpenAI's ``prompt_cache_key`` so repeated
        instruction prefixes are billed at the cached-input rate.
        """
        extra = {"prompt_cache_key": cache_key} if cache_key else {}
        response = await self.sdk.responses.parse(
            model=self.model,
            instructions=instructions,
            input=input_text,
            text_format=output_schema,
            **extra,
        )
        if response.output_parsed is None:
            reason = getattr(response.incomplete_details, "reason", None)
            raise ValueError(
                f"OpenAI returned no parsed structured output "
                f"(status={response.status}, reason={reason})."
            )

        usage = response.usage
        details = usage.input_tokens_details if usage is not None else None
        return StructuredResult(
            output=response.output_parsed,
            input_tokens=usage.input_tokens if usage else 0,
            output_tokens=usage.output_tokens if usage else 0,
            cached_input_tokens=(details.cached_tokens or 0) if details else 0,
            cache_write_tokens=(getattr(details, "cache_write_tokens", 0) or 0) if details else 0,
        )

    async def close(self) -> None:
        """Release SDK HTTP resources without making an API request."""
        await self.sdk.close()

"""Per-stage token usage and cost accounting for one analysis run."""

from dataclasses import dataclass, field
from typing import Any

from app.llm.pricing import ModelPricing, request_cost_usd

# Rough heuristic for pre-call estimates (OpenAI averages ~4 chars per token).
CHARS_PER_TOKEN = 4

_COUNTERS = ("input_tokens", "output_tokens", "cached_input_tokens", "cache_write_tokens")


def estimate_tokens(text: str) -> int:
    """Cheap token estimate used by the cost guard before calling the API."""
    return max(1, len(text) // CHARS_PER_TOKEN)


@dataclass
class UsageTracker:
    """Accumulate token usage and cost per stage; JSON-serializable summary."""

    model: str
    pricing: ModelPricing | None = None
    stages: dict[str, dict[str, Any]] = field(default_factory=dict)

    def record(
        self,
        stage: str,
        input_tokens: int,
        output_tokens: int,
        cached_input_tokens: int = 0,
        cache_write_tokens: int = 0,
    ) -> None:
        """Record one API request (cost is computed per request)."""
        bucket = self.stages.setdefault(
            stage, {**{c: 0 for c in _COUNTERS}, "requests": 0, "cost_usd": 0.0}
        )
        bucket["input_tokens"] += input_tokens
        bucket["output_tokens"] += output_tokens
        bucket["cached_input_tokens"] += cached_input_tokens
        bucket["cache_write_tokens"] += cache_write_tokens
        if input_tokens or output_tokens:
            bucket["requests"] += 1
        cost = request_cost_usd(
            self.pricing, input_tokens, output_tokens, cached_input_tokens, cache_write_tokens
        )
        if cost is None or bucket["cost_usd"] is None:
            bucket["cost_usd"] = None
        else:
            bucket["cost_usd"] += cost

    @property
    def spent_usd(self) -> float | None:
        """Cost so far, or None when the model has no pricing."""
        if self.pricing is None:
            return None
        return sum(s["cost_usd"] or 0.0 for s in self.stages.values())

    def to_dict(self) -> dict[str, Any]:
        totals = {c: sum(s[c] for s in self.stages.values()) for c in _COUNTERS}
        spent = self.spent_usd
        return {
            "model": self.model,
            "stages": {
                name: {
                    **counts,
                    "cost_usd": None if counts["cost_usd"] is None else round(counts["cost_usd"], 6),
                }
                for name, counts in self.stages.items()
            },
            **totals,
            "total_tokens": totals["input_tokens"] + totals["output_tokens"],
            "estimated_cost_usd": None if spent is None else round(spent, 6),
            "pricing_configured": self.pricing is not None,
        }

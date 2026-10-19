"""Per-stage token usage and cost accounting for one analysis run."""

from dataclasses import dataclass, field
from typing import Any

# Rough heuristic for pre-call estimates (OpenAI averages ~4 chars per token).
CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Cheap token estimate used by the cost guard before calling the API."""
    return max(1, len(text) // CHARS_PER_TOKEN)


def compute_cost_usd(
    input_tokens: int,
    output_tokens: int,
    price_input_per_1m: float | None,
    price_output_per_1m: float | None,
) -> float | None:
    """Return USD cost, or None when pricing is not configured."""
    if price_input_per_1m is None or price_output_per_1m is None:
        return None
    cost = (
        input_tokens * price_input_per_1m + output_tokens * price_output_per_1m
    ) / 1_000_000
    return round(cost, 6)


@dataclass
class UsageTracker:
    """Accumulate token usage per stage and expose a JSON-serializable summary."""

    model: str
    price_input_per_1m: float | None = None
    price_output_per_1m: float | None = None
    stages: dict[str, dict[str, int]] = field(default_factory=dict)

    def record(
        self,
        stage: str,
        input_tokens: int,
        output_tokens: int,
        cached_input_tokens: int = 0,
    ) -> None:
        bucket = self.stages.setdefault(
            stage, {"input_tokens": 0, "output_tokens": 0, "cached_input_tokens": 0}
        )
        bucket["input_tokens"] += input_tokens
        bucket["output_tokens"] += output_tokens
        bucket["cached_input_tokens"] += cached_input_tokens

    def to_dict(self) -> dict[str, Any]:
        total_in = sum(s["input_tokens"] for s in self.stages.values())
        total_out = sum(s["output_tokens"] for s in self.stages.values())
        total_cached = sum(s["cached_input_tokens"] for s in self.stages.values())
        return {
            "model": self.model,
            "stages": {
                name: {
                    **counts,
                    "cost_usd": compute_cost_usd(
                        counts["input_tokens"],
                        counts["output_tokens"],
                        self.price_input_per_1m,
                        self.price_output_per_1m,
                    ),
                }
                for name, counts in self.stages.items()
            },
            "input_tokens": total_in,
            "output_tokens": total_out,
            "cached_input_tokens": total_cached,
            "total_tokens": total_in + total_out,
            # Upper bound: cached input is billed at a discount we don't model.
            "estimated_cost_usd": compute_cost_usd(
                total_in, total_out, self.price_input_per_1m, self.price_output_per_1m
            ),
            "pricing_configured": (
                self.price_input_per_1m is not None
                and self.price_output_per_1m is not None
            ),
        }

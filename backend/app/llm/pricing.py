"""Model price table, per-request cost, and project budget checks.

Prices are USD per 1M tokens, copied from OpenAI's model pages. Update
``PRICE_TABLE`` when prices change or a new model is added.
"""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

PER_MILLION = 1_000_000


@dataclass(frozen=True)
class ModelPricing:
    input_per_1m: float
    cached_input_per_1m: float
    output_per_1m: float
    cache_write_per_1m: float
    # Requests above this many input tokens are billed at the long-context rates.
    long_context_threshold: int | None = None
    long_context_input_multiplier: float = 1.0
    long_context_output_multiplier: float = 1.0


PRICE_TABLE: dict[str, ModelPricing] = {
    "gpt-5.6-luna": ModelPricing(
        input_per_1m=0.20,
        cached_input_per_1m=0.02,
        output_per_1m=1.20,
        cache_write_per_1m=0.25,
        long_context_threshold=272_000,
        long_context_input_multiplier=2.0,
        long_context_output_multiplier=1.5,
    ),
}

BUDGET_WARNING_THRESHOLDS = (0.5, 0.8)


def get_pricing(model: str) -> ModelPricing | None:
    """Return pricing for ``model`` or None when it is not in the table."""
    return PRICE_TABLE.get(model.strip())


def request_cost_usd(
    pricing: ModelPricing | None,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> float | None:
    """Cost of one API request; ``input_tokens`` includes cached and written tokens."""
    if pricing is None:
        return None
    in_mult = out_mult = 1.0
    if pricing.long_context_threshold and input_tokens > pricing.long_context_threshold:
        in_mult = pricing.long_context_input_multiplier
        out_mult = pricing.long_context_output_multiplier

    uncached = max(0, input_tokens - cached_input_tokens - cache_write_tokens)
    cost = (
        uncached * pricing.input_per_1m
        + cached_input_tokens * pricing.cached_input_per_1m
        + cache_write_tokens * pricing.cache_write_per_1m
    ) * in_mult + output_tokens * pricing.output_per_1m * out_mult
    return cost / PER_MILLION


def check_project_budget(
    total_spent_usd: float,
    budget_usd: float,
    next_run_estimate_usd: float = 0.0,
) -> dict[str, Any]:
    """Check cumulative spend against the project budget.

    ``total_spent_usd`` is the sum of ``usage.estimated_cost_usd`` over all
    previous runs (Person 3 supplies it). Logs a warning once spend passes
    50% and 80% of the budget. ``allowed`` is False when the next run's
    estimate would push spend over the budget.
    """
    spent = max(0.0, float(total_spent_usd))
    fraction = spent / budget_usd if budget_usd > 0 else 1.0
    crossed = [t for t in BUDGET_WARNING_THRESHOLDS if fraction >= t]
    if crossed:
        logger.warning(
            "LLM project budget: $%.2f of $%.2f spent (%.0f%%, past the %.0f%% threshold).",
            spent,
            budget_usd,
            fraction * 100,
            max(crossed) * 100,
        )
    return {
        "budget_usd": budget_usd,
        "spent_usd": round(spent, 6),
        "remaining_usd": round(max(0.0, budget_usd - spent), 6),
        "fraction_used": round(fraction, 4),
        "thresholds_crossed": crossed,
        "allowed": spent + next_run_estimate_usd <= budget_usd,
    }

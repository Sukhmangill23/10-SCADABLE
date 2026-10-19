"""Conservative per-competitor reservations, separate from authoritative API billing."""

import json
import math
from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal

INPUT_USD_PER_MILLION = Decimal("0.10")
MAX_REQUEST_BYTES = 48 * 1024
RESERVATION_OVERHEAD = 1024


def request_size(payload: dict) -> int:
    """Measure the complete request, including questions and their rubric descriptions."""
    return len(json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8"))


@dataclass(frozen=True, eq=False)
class _Reservation:
    tokens: int


class DecisionBudget:
    """Synchronous ledger operations are atomic within the owning asyncio event loop.

    Reserve immediately before dispatch. Unknown-usage requests keep their full
    estimate; successful responses replace the estimate with reported input usage.
    Regional premiums, tokenization, and billing adjustments can differ from this
    base-rate estimate. This is not a hard invoice cap.
    """

    def __init__(self, budget_usd: float):
        if not math.isfinite(budget_usd) or budget_usd < 0:
            raise ValueError("Decision budget must be finite and nonnegative")
        tokens = Decimal(str(budget_usd)) * 1_000_000 / INPUT_USD_PER_MILLION
        self.limit_tokens = int(tokens.to_integral_value(rounding=ROUND_FLOOR))
        self.reported_input_tokens = 0
        self.uncertain_input_tokens = 0
        self.request_count = 0
        self._reservations: set[_Reservation] = set()

    @property
    def reserved_tokens(self) -> int:
        return sum(item.tokens for item in self._reservations)

    @property
    def estimated_cost_usd(self) -> float:
        tokens = self.reported_input_tokens + self.uncertain_input_tokens + self.reserved_tokens
        return float(Decimal(tokens) * INPUT_USD_PER_MILLION / 1_000_000)

    def reserve(self, payload: dict) -> _Reservation | None:
        size = request_size(payload)
        if size > MAX_REQUEST_BYTES:
            raise ValueError("Decision request exceeds 48 KiB")
        estimate = size + RESERVATION_OVERHEAD
        committed = self.reported_input_tokens + self.uncertain_input_tokens + self.reserved_tokens
        if committed + estimate > self.limit_tokens:
            return None
        reservation = _Reservation(estimate)
        self._reservations.add(reservation)
        self.request_count += 1
        return reservation

    def settle(self, reservation: _Reservation, *, reported_input_tokens: int | None) -> None:
        if reservation not in self._reservations:
            raise ValueError("Reservation was already settled or belongs to a different budget")
        if reported_input_tokens is not None and (
            type(reported_input_tokens) is not int or reported_input_tokens < 0
        ):
            raise ValueError("Reported token usage must be a nonnegative integer")
        self._reservations.remove(reservation)
        if reported_input_tokens is None:
            self.uncertain_input_tokens += reservation.tokens
        else:
            self.reported_input_tokens += reported_input_tokens

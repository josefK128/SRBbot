from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .models import Observation, Snapshot


@dataclass(frozen=True)
class Decision:
    strategy: str
    action: str
    held_netuid: int | None
    candidate_netuid: int
    held_value: Decimal | None
    candidate_value: Decimal
    threshold: Decimal | None
    reason: str


def _best(snapshot: Snapshot, strategy: str) -> Observation:
    key = (lambda item: item.score) if strategy == "score" else (lambda item: item.delta_price_1h)
    return max(snapshot.observations, key=lambda item: (key(item), -item.netuid))


def decide(snapshot: Snapshot, strategy: str, held_netuid: int | None) -> Decision:
    if strategy not in {"score", "breakout"}:
        raise ValueError(f"unknown strategy: {strategy}")
    candidate = _best(snapshot, strategy)
    candidate_value = candidate.score if strategy == "score" else candidate.delta_price_1h
    if held_netuid is None:
        return Decision(
            strategy, "ENTER", None, candidate.netuid, None, candidate_value, None, "INITIAL_ENTRY"
        )
    observations = snapshot.by_netuid()
    if held_netuid not in observations:
        raise ValueError(f"held subnet {held_netuid} missing from snapshot")
    held = observations[held_netuid]
    held_value = held.score if strategy == "score" else held.delta_price_1h
    if candidate.netuid == held_netuid:
        return Decision(
            strategy,
            "HOLD",
            held_netuid,
            candidate.netuid,
            held_value,
            candidate_value,
            None,
            "BEST_IS_HELD",
        )
    threshold = held_value * Decimal("1.1")
    if strategy == "breakout":
        threshold = max(threshold, Decimal("0.01"))
    if candidate_value > threshold:
        return Decision(
            strategy,
            "REPLACE",
            held_netuid,
            candidate.netuid,
            held_value,
            candidate_value,
            threshold,
            "THRESHOLD_CLEARED",
        )
    return Decision(
        strategy,
        "HOLD",
        held_netuid,
        candidate.netuid,
        held_value,
        candidate_value,
        threshold,
        "THRESHOLD_NOT_CLEARED",
    )


def decide_conditional(
    snapshot: Snapshot, held_netuid: int | None, tao_market: int | None
) -> Decision:
    """Use Breakout in directional TAO markets and Score when static."""
    active_strategy = "breakout" if tao_market in (-1, 1) else "score"
    base = decide(snapshot, active_strategy, held_netuid)
    return Decision(
        strategy="conditional",
        action=base.action,
        held_netuid=base.held_netuid,
        candidate_netuid=base.candidate_netuid,
        held_value=base.held_value,
        candidate_value=base.candidate_value,
        threshold=base.threshold,
        reason=f"{active_strategy.upper()}_{base.reason}",
    )

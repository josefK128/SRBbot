from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

TAO_SCALE = 1_000_000_000


def decimal(value: object) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError("numeric value is required")
    return Decimal(str(value))


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(UTC)


@dataclass(frozen=True)
class Observation:
    netuid: int
    score: Decimal
    delta_price_1h: Decimal
    price_tao: Decimal

    def __post_init__(self) -> None:
        if self.netuid < 0:
            raise ValueError("netuid must be non-negative")
        if not Decimal("0") <= self.score <= Decimal("100"):
            raise ValueError("score must be in [0, 100]")
        if self.price_tao <= 0:
            raise ValueError("price_tao must be positive")


@dataclass(frozen=True)
class Snapshot:
    snapshot_id: str
    sampled_at: datetime
    tao_price_usd: Decimal
    observations: tuple[Observation, ...]
    schema_version: str = "1"

    def __post_init__(self) -> None:
        if self.tao_price_usd <= 0:
            raise ValueError("tao_price_usd must be positive")

    def by_netuid(self) -> dict[int, Observation]:
        return {item.netuid: item for item in self.observations}

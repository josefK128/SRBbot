from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal

from .models import TAO_SCALE


@dataclass(frozen=True)
class CostModel:
    stake_fee_bps: int = 5
    unstake_fee_bps: int = 5
    slippage_bps: int = 25
    network_fee_rao: int = 100_000

    def __post_init__(self) -> None:
        if (
            min(
                self.stake_fee_bps,
                self.unstake_fee_bps,
                self.slippage_bps,
                self.network_fee_rao,
            )
            < 0
        ):
            raise ValueError("cost basis points cannot be negative")
        if max(self.stake_fee_bps, self.unstake_fee_bps, self.slippage_bps) >= 10_000:
            raise ValueError("cost basis points must be below 10000")

    @staticmethod
    def _cost(amount_rao: int, bps: int) -> int:
        return (amount_rao * bps) // 10_000

    def stake(self, free_rao: int, price_tao: Decimal) -> tuple[int, Decimal, int]:
        fee = self._cost(free_rao, self.stake_fee_bps + self.slippage_bps) + self.network_fee_rao
        if fee >= free_rao:
            raise ValueError("stake costs consume the available TAO")
        invested = free_rao - fee
        alpha = (Decimal(invested) / TAO_SCALE / price_tao).quantize(
            Decimal("0.000000000000000001"), rounding=ROUND_DOWN
        )
        return 0, alpha, fee

    def unstake(self, alpha: Decimal, price_tao: Decimal) -> tuple[int, int]:
        gross = int((alpha * price_tao * TAO_SCALE).to_integral_value(rounding=ROUND_DOWN))
        fee = self._cost(gross, self.unstake_fee_bps + self.slippage_bps) + self.network_fee_rao
        if fee >= gross:
            raise ValueError("unstake costs consume the gross proceeds")
        return gross - fee, fee

    def liquidation_value(self, alpha: Decimal, price_tao: Decimal) -> int:
        return self.unstake(alpha, price_tao)[0]

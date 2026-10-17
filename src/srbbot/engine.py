from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from .broker import CostModel
from .models import Snapshot
from .strategy import Decision, decide, decide_conditional

TAO_MARKET_THRESHOLD = Decimal("0.01")


class DuplicateSnapshot(ValueError):
    pass


class TimeReversal(ValueError):
    pass


def classify_tao_market(
    current_price: Decimal, previous_price: Decimal | None
) -> tuple[Decimal | None, int | None]:
    """Return fractional TAO price change and its -1/0/1 market regime."""
    if previous_price is None:
        return None, None
    change = (current_price - previous_price) / previous_price
    if change > TAO_MARKET_THRESHOLD:
        return change, 1
    if change < -TAO_MARKET_THRESHOLD:
        return change, -1
    return change, 0


class Engine:
    def __init__(self, connection: sqlite3.Connection, costs: CostModel | None = None) -> None:
        self.db = connection
        self.costs = costs or CostModel()
        self._lock = threading.RLock()

    def process(self, snapshot: Snapshot, payload: dict[str, Any]) -> list[Decision]:
        with self._lock:
            return self._process(snapshot, payload)

    def _process(self, snapshot: Snapshot, payload: dict[str, Any]) -> list[Decision]:
        latest = self.db.execute(
            "SELECT snapshot_id,sampled_at,tao_price_usd FROM snapshots "
            "ORDER BY sampled_at DESC LIMIT 1"
        ).fetchone()
        if latest and latest["snapshot_id"] == snapshot.snapshot_id:
            raise DuplicateSnapshot(snapshot.snapshot_id)
        sampled_at = snapshot.sampled_at.isoformat()
        if latest and sampled_at <= latest["sampled_at"]:
            raise TimeReversal(f"snapshot {sampled_at} is not later than {latest['sampled_at']}")
        previous_tao_price = Decimal(latest["tao_price_usd"]) if latest else None
        tao_price_change, tao_market = classify_tao_market(
            snapshot.tao_price_usd, previous_tao_price
        )
        decisions: list[Decision] = []
        with self.db:
            self.db.execute(
                "INSERT INTO snapshots"
                "(snapshot_id,sampled_at,received_at,schema_version,tao_price_usd,payload_json,"
                "previous_tao_price_usd,tao_price_change,tao_market) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    snapshot.snapshot_id,
                    sampled_at,
                    datetime.now(UTC).isoformat(),
                    snapshot.schema_version,
                    str(snapshot.tao_price_usd),
                    json.dumps(payload, sort_keys=True, separators=(",", ":")),
                    None if previous_tao_price is None else str(previous_tao_price),
                    None if tao_price_change is None else str(tao_price_change),
                    tao_market,
                ),
            )
            self.db.executemany(
                "INSERT INTO observations VALUES(?,?,?,?,?)",
                [
                    (
                        snapshot.snapshot_id,
                        item.netuid,
                        str(item.score),
                        str(item.delta_price_1h),
                        str(item.price_tao),
                    )
                    for item in snapshot.observations
                ],
            )
            for strategy in ("score", "breakout", "conditional"):
                portfolio = self.db.execute(
                    "SELECT * FROM portfolios WHERE strategy=?", (strategy,)
                ).fetchone()
                decision = (
                    decide_conditional(snapshot, portfolio["held_netuid"], tao_market)
                    if strategy == "conditional"
                    else decide(snapshot, strategy, portfolio["held_netuid"])
                )
                decisions.append(decision)
                cursor = self.db.execute(
                    "INSERT INTO decisions(snapshot_id,strategy,action,held_netuid,"
                    "candidate_netuid,held_value,candidate_value,threshold,reason) "
                    "VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        snapshot.snapshot_id,
                        strategy,
                        decision.action,
                        decision.held_netuid,
                        decision.candidate_netuid,
                        None if decision.held_value is None else str(decision.held_value),
                        str(decision.candidate_value),
                        None if decision.threshold is None else str(decision.threshold),
                        decision.reason,
                    ),
                )
                self._execute(
                    cursor.lastrowid,
                    decision,
                    snapshot,
                    portfolio,
                    previous_tao_price,
                    tao_price_change,
                    tao_market,
                )
        return decisions

    def _execute(
        self,
        decision_id: int,
        decision: Decision,
        snapshot: Snapshot,
        portfolio: sqlite3.Row,
        previous_tao_price: Decimal | None,
        tao_price_change: Decimal | None,
        tao_market: int | None,
    ) -> None:
        observations = snapshot.by_netuid()
        free = int(portfolio["free_rao"])
        alpha = Decimal(portfolio["alpha_units"])
        held = portfolio["held_netuid"]
        total_cost = int(portfolio["total_cost_rao"])
        if decision.action == "REPLACE":
            proceeds, fee = self.costs.unstake(alpha, observations[held].price_tao)
            self.db.execute(
                "INSERT INTO fills(decision_id,side,netuid,tao_rao,alpha_units,fee_rao)"
                " VALUES(?,?,?,?,?,?)",
                (decision_id, "UNSTAKE", held, proceeds, str(alpha), fee),
            )
            free += proceeds
            total_cost += fee
            alpha = Decimal(0)
        if decision.action in {"ENTER", "REPLACE"}:
            before = free
            free, alpha, fee = self.costs.stake(
                free, observations[decision.candidate_netuid].price_tao
            )
            held = decision.candidate_netuid
            total_cost += fee
            self.db.execute(
                "INSERT INTO fills(decision_id,side,netuid,tao_rao,alpha_units,fee_rao)"
                " VALUES(?,?,?,?,?,?)",
                (decision_id, "STAKE", held, before - fee, str(alpha), fee),
            )
        self.db.execute(
            "UPDATE portfolios SET free_rao=?,held_netuid=?,alpha_units=?,"
            "total_cost_rao=? WHERE strategy=?",
            (free, held, str(alpha), total_cost, decision.strategy),
        )
        nav = free + (
            self.costs.liquidation_value(alpha, observations[held].price_tao)
            if held is not None
            else 0
        )
        nav_usd = (Decimal(nav) / 1_000_000_000 * snapshot.tao_price_usd).quantize(
            Decimal("0.00000001")
        )
        initial = int(portfolio["initial_rao"])
        return_percent = ((Decimal(nav) / Decimal(initial) - Decimal(1)) * Decimal(100)).quantize(
            Decimal("0.000001")
        )
        self.db.execute(
            "INSERT INTO positions_nav"
            "(snapshot_id,strategy,held_netuid,free_rao,alpha_units,nav_rao,"
            "return_percent,tao_price_usd,nav_usd,previous_tao_price_usd,"
            "tao_price_change,tao_market) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                snapshot.snapshot_id,
                decision.strategy,
                held,
                free,
                str(alpha),
                nav,
                str(return_percent),
                str(snapshot.tao_price_usd),
                str(nav_usd),
                None if previous_tao_price is None else str(previous_tao_price),
                None if tao_price_change is None else str(tao_price_change),
                tao_market,
            ),
        )

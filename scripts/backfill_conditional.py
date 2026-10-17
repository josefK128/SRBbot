from __future__ import annotations

import argparse
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from srbbot.broker import CostModel
from srbbot.database import connect
from srbbot.engine import Engine
from srbbot.models import Observation, Snapshot
from srbbot.strategy import decide_conditional


def backfill(path: Path) -> None:
    db = connect(path)
    snapshot_count = db.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
    decision_count = db.execute(
        "SELECT COUNT(*) FROM decisions WHERE strategy='conditional'"
    ).fetchone()[0]
    nav_count = db.execute(
        "SELECT COUNT(*) FROM positions_nav WHERE strategy='conditional'"
    ).fetchone()[0]
    if decision_count == snapshot_count and nav_count == snapshot_count:
        print(f"conditional backfill already complete: {snapshot_count} snapshots")
        return
    if decision_count or nav_count:
        raise RuntimeError(
            f"partial conditional history exists: decisions={decision_count}, nav={nav_count}"
        )
    portfolio = db.execute(
        "SELECT * FROM portfolios WHERE strategy='conditional'"
    ).fetchone()
    if (
        portfolio["free_rao"] != 100_000_000_000
        or portfolio["held_netuid"] is not None
        or Decimal(portfolio["alpha_units"]) != 0
        or portfolio["total_cost_rao"] != 0
    ):
        raise RuntimeError("conditional portfolio is not pristine")

    engine = Engine(db, CostModel())
    snapshots = db.execute("SELECT * FROM snapshots ORDER BY sampled_at").fetchall()
    with db:
        for row in snapshots:
            observation_rows = db.execute(
                "SELECT * FROM observations WHERE snapshot_id=? ORDER BY netuid",
                (row["snapshot_id"],),
            ).fetchall()
            snapshot = Snapshot(
                snapshot_id=row["snapshot_id"],
                sampled_at=datetime.fromisoformat(row["sampled_at"]),
                tao_price_usd=Decimal(row["tao_price_usd"]),
                schema_version=row["schema_version"],
                observations=tuple(
                    Observation(
                        netuid=item["netuid"],
                        score=Decimal(item["score"]),
                        delta_price_1h=Decimal(item["delta_price_1h"]),
                        price_tao=Decimal(item["price_tao"]),
                    )
                    for item in observation_rows
                ),
            )
            portfolio = db.execute(
                "SELECT * FROM portfolios WHERE strategy='conditional'"
            ).fetchone()
            decision = decide_conditional(
                snapshot, portfolio["held_netuid"], row["tao_market"]
            )
            cursor = db.execute(
                "INSERT INTO decisions(snapshot_id,strategy,action,held_netuid,"
                "candidate_netuid,held_value,candidate_value,threshold,reason) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    snapshot.snapshot_id,
                    decision.strategy,
                    decision.action,
                    decision.held_netuid,
                    decision.candidate_netuid,
                    None if decision.held_value is None else str(decision.held_value),
                    str(decision.candidate_value),
                    None if decision.threshold is None else str(decision.threshold),
                    decision.reason,
                ),
            )
            engine._execute(
                cursor.lastrowid,
                decision,
                snapshot,
                portfolio,
                None
                if row["previous_tao_price_usd"] is None
                else Decimal(row["previous_tao_price_usd"]),
                None if row["tao_price_change"] is None else Decimal(row["tao_price_change"]),
                row["tao_market"],
            )

    final_decisions = db.execute(
        "SELECT COUNT(*) FROM decisions WHERE strategy='conditional'"
    ).fetchone()[0]
    final_nav = db.execute(
        "SELECT COUNT(*) FROM positions_nav WHERE strategy='conditional'"
    ).fetchone()[0]
    if (final_decisions, final_nav) != (snapshot_count, snapshot_count):
        raise RuntimeError(
            f"backfill verification failed: decisions={final_decisions}, nav={final_nav}"
        )
    portfolio = db.execute(
        "SELECT held_netuid,total_cost_rao FROM portfolios WHERE strategy='conditional'"
    ).fetchone()
    print(
        f"backfilled conditional across {snapshot_count} snapshots; "
        f"held_netuid={portfolio['held_netuid']}; total_cost_rao={portfolio['total_cost_rao']}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    args = parser.parse_args()
    backfill(args.database)

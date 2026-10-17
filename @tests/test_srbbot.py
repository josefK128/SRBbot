import sqlite3
from copy import deepcopy
from decimal import Decimal

import pytest

from srbbot.broker import CostModel
from srbbot.client import SnapshotError, normalize_snapshot
from srbbot.database import connect
from srbbot.engine import DuplicateSnapshot, Engine, TimeReversal, classify_tao_market
from srbbot.strategy import decide, decide_conditional


def payload(snapshot_id="one", sampled_at="2026-10-09T18:00:00Z"):
    return {
        "snapshot_id": snapshot_id,
        "sampled_at": sampled_at,
        "schema_version": "1",
        "tao_price_usd": "300",
        "subnets": [
            {"netuid": 1, "score": "80", "delta_price_1h": "0.02", "price_tao": "0.5"},
            {"netuid": 2, "score": "70", "delta_price_1h": "0.08", "price_tao": "1"},
        ],
    }


def test_initial_entries_and_independent_hundred_tao_ledgers(tmp_path):
    db = connect(tmp_path / "test.sqlite3")
    result = Engine(db).process(normalize_snapshot(payload()), payload())
    assert [(item.strategy, item.action, item.candidate_netuid) for item in result] == [
        ("score", "ENTER", 1),
        ("breakout", "ENTER", 2),
        ("conditional", "ENTER", 1),
    ]
    rows = db.execute(
        "SELECT strategy,initial_rao,held_netuid FROM portfolios ORDER BY strategy"
    ).fetchall()
    assert [(row["strategy"], row["initial_rao"], row["held_netuid"]) for row in rows] == [
        ("breakout", 100_000_000_000, 2),
        ("conditional", 100_000_000_000, 1),
        ("score", 100_000_000_000, 1),
    ]


def test_conditional_uses_breakout_when_tao_market_is_directional():
    snapshot = normalize_snapshot(payload())
    initial = decide_conditional(snapshot, None, None)
    assert (initial.strategy, initial.candidate_netuid, initial.reason) == (
        "conditional", 1, "SCORE_INITIAL_ENTRY"
    )
    static = decide_conditional(snapshot, 1, 0)
    assert (static.action, static.candidate_netuid, static.reason) == (
        "HOLD", 1, "SCORE_BEST_IS_HELD"
    )
    falling = decide_conditional(snapshot, 1, -1)
    assert (falling.action, falling.candidate_netuid, falling.reason) == (
        "REPLACE", 2, "BREAKOUT_THRESHOLD_CLEARED"
    )
    rising = decide_conditional(snapshot, 1, 1)
    assert (rising.action, rising.candidate_netuid, rising.reason) == (
        "REPLACE", 2, "BREAKOUT_THRESHOLD_CLEARED"
    )


def test_strict_thresholds():
    second = deepcopy(payload("two", "2026-10-09T19:00:00Z"))
    second["subnets"][1]["score"] = "88"
    assert decide(normalize_snapshot(second), "score", 1).action == "HOLD"
    second["subnets"][1]["score"] = "88.01"
    assert decide(normalize_snapshot(second), "score", 1).action == "REPLACE"
    second["subnets"][0]["delta_price_1h"] = "-0.10"
    second["subnets"][1]["delta_price_1h"] = "0.01"
    assert decide(normalize_snapshot(second), "breakout", 1).action == "HOLD"
    second["subnets"][1]["delta_price_1h"] = "0.0101"
    assert decide(normalize_snapshot(second), "breakout", 1).action == "REPLACE"


def test_replacement_costs_and_nav_are_persisted(tmp_path):
    db = connect(tmp_path / "costs.sqlite3")
    engine = Engine(db, CostModel(stake_fee_bps=10, unstake_fee_bps=10))
    first = payload()
    engine.process(normalize_snapshot(first), first)
    second = deepcopy(payload("two", "2026-10-09T19:00:00Z"))
    second["subnets"][1]["score"] = "90"
    engine.process(normalize_snapshot(second), second)
    portfolio = db.execute("SELECT * FROM portfolios WHERE strategy='score'").fetchone()
    assert portfolio["held_netuid"] == 2
    assert portfolio["total_cost_rao"] > 0
    nav = db.execute(
        "SELECT * FROM positions_nav WHERE snapshot_id='two' AND strategy='score'"
    ).fetchone()
    assert nav["tao_price_usd"] == "300"
    assert Decimal(nav["nav_usd"]) > 0
    assert Decimal(nav["return_percent"]) < 0


def test_duplicate_and_time_reversal_fail_closed(tmp_path):
    db = connect(tmp_path / "order.sqlite3")
    engine = Engine(db)
    first = payload()
    engine.process(normalize_snapshot(first), first)
    with pytest.raises(DuplicateSnapshot):
        engine.process(normalize_snapshot(first), first)
    old = payload("old", "2026-10-09T17:00:00Z")
    with pytest.raises(TimeReversal):
        engine.process(normalize_snapshot(old), old)


def test_invalid_score_and_missing_field_rejected():
    bad = payload()
    bad["subnets"][0]["score"] = "101"
    with pytest.raises(SnapshotError):
        normalize_snapshot(bad)
    missing = payload()
    del missing["subnets"][0]["price_tao"]
    with pytest.raises(SnapshotError):
        normalize_snapshot(missing)


def test_old_initial_balance_database_is_rejected(tmp_path):
    path = tmp_path / "old.sqlite3"
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE portfolios (strategy TEXT PRIMARY KEY, initial_rao INTEGER NOT NULL, "
        "free_rao INTEGER NOT NULL, held_netuid INTEGER, alpha_units TEXT NOT NULL, "
        "total_cost_rao INTEGER NOT NULL DEFAULT 0)"
    )
    db.execute("INSERT INTO portfolios VALUES('score',10000000000,0,1,'20',0)")
    db.commit()
    db.close()
    with pytest.raises(RuntimeError, match="fresh database"):
        connect(path)


def test_frozen_default_cost_model():
    costs = CostModel()
    free, alpha, fee = costs.stake(100_000_000_000, Decimal("1"))
    assert free == 0
    assert fee == 300_100_000
    assert alpha == Decimal("99.699900000000000000")


def test_tao_market_change_is_classified_and_persisted_for_both_strategies(tmp_path):
    db = connect(tmp_path / "market.sqlite3")
    engine = Engine(db)
    first = payload()
    engine.process(normalize_snapshot(first), first)
    second = payload("two", "2026-10-09T19:00:00Z")
    second["tao_price_usd"] = "303"
    engine.process(normalize_snapshot(second), second)
    third = payload("three", "2026-10-09T20:00:00Z")
    third["tao_price_usd"] = "299.87"
    engine.process(normalize_snapshot(third), third)

    first_rows = db.execute(
        "SELECT tao_market,previous_tao_price_usd FROM positions_nav WHERE snapshot_id='one'"
    ).fetchall()
    assert len(first_rows) == 3
    assert all(row["tao_market"] is None for row in first_rows)
    assert all(row["previous_tao_price_usd"] is None for row in first_rows)

    second_rows = db.execute(
        "SELECT tao_market,previous_tao_price_usd,tao_price_change "
        "FROM positions_nav WHERE snapshot_id='two'"
    ).fetchall()
    assert len(second_rows) == 3
    assert all(row["tao_market"] == 0 for row in second_rows)
    assert all(row["previous_tao_price_usd"] == "300" for row in second_rows)
    assert all(Decimal(row["tao_price_change"]) == Decimal("0.01") for row in second_rows)

    third_rows = db.execute(
        "SELECT tao_market FROM positions_nav WHERE snapshot_id='three'"
    ).fetchall()
    assert all(row["tao_market"] == -1 for row in third_rows)


@pytest.mark.parametrize(
    ("current", "previous", "expected"),
    [
        ("101.01", "100", 1),
        ("101", "100", 0),
        ("99", "100", 0),
        ("98.99", "100", -1),
    ],
)
def test_tao_market_boundaries(current, previous, expected):
    _, market = classify_tao_market(Decimal(current), Decimal(previous))
    assert market == expected

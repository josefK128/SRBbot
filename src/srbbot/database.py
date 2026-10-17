from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS snapshots (
  snapshot_id TEXT PRIMARY KEY, sampled_at TEXT NOT NULL UNIQUE,
  received_at TEXT NOT NULL, schema_version TEXT NOT NULL,
  tao_price_usd TEXT NOT NULL, payload_json TEXT NOT NULL,
  previous_tao_price_usd TEXT, tao_price_change TEXT,
  tao_market INTEGER CHECK (tao_market IN (-1, 0, 1))
);
CREATE TABLE IF NOT EXISTS observations (
  snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id), netuid INTEGER NOT NULL,
  score TEXT NOT NULL, delta_price_1h TEXT NOT NULL, price_tao TEXT NOT NULL,
  PRIMARY KEY (snapshot_id, netuid)
);
CREATE TABLE IF NOT EXISTS portfolios (
  strategy TEXT PRIMARY KEY, initial_rao INTEGER NOT NULL, free_rao INTEGER NOT NULL,
  held_netuid INTEGER, alpha_units TEXT NOT NULL, total_cost_rao INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS decisions (
  id INTEGER PRIMARY KEY, snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
  strategy TEXT NOT NULL, action TEXT NOT NULL, held_netuid INTEGER,
  candidate_netuid INTEGER NOT NULL, held_value TEXT, candidate_value TEXT NOT NULL,
  threshold TEXT, reason TEXT NOT NULL, UNIQUE(snapshot_id, strategy)
);
CREATE TABLE IF NOT EXISTS fills (
  id INTEGER PRIMARY KEY, decision_id INTEGER NOT NULL REFERENCES decisions(id),
  side TEXT NOT NULL, netuid INTEGER NOT NULL, tao_rao INTEGER NOT NULL,
  alpha_units TEXT NOT NULL, fee_rao INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS positions_nav (
  snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id), strategy TEXT NOT NULL,
  held_netuid INTEGER, free_rao INTEGER NOT NULL, alpha_units TEXT NOT NULL,
  nav_rao INTEGER NOT NULL, return_percent TEXT NOT NULL,
  tao_price_usd TEXT NOT NULL, nav_usd TEXT NOT NULL,
  previous_tao_price_usd TEXT, tao_price_change TEXT,
  tao_market INTEGER CHECK (tao_market IN (-1, 0, 1)),
  PRIMARY KEY(snapshot_id, strategy)
);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    snapshot_columns = {row["name"] for row in connection.execute("PRAGMA table_info(snapshots)")}
    for name, sql_type in (
        ("previous_tao_price_usd", "TEXT"),
        ("tao_price_change", "TEXT"),
        ("tao_market", "INTEGER"),
    ):
        if name not in snapshot_columns:
            connection.execute(f"ALTER TABLE snapshots ADD COLUMN {name} {sql_type}")
    nav_columns = {row["name"] for row in connection.execute("PRAGMA table_info(positions_nav)")}
    if "return_percent" not in nav_columns:
        connection.execute(
            "ALTER TABLE positions_nav ADD COLUMN return_percent TEXT NOT NULL DEFAULT '0'"
        )
    for name, sql_type in (
        ("previous_tao_price_usd", "TEXT"),
        ("tao_price_change", "TEXT"),
        ("tao_market", "INTEGER"),
    ):
        if name not in nav_columns:
            connection.execute(f"ALTER TABLE positions_nav ADD COLUMN {name} {sql_type}")
    for strategy in ("score", "breakout", "conditional"):
        connection.execute(
            "INSERT OR IGNORE INTO portfolios"
            "(strategy,initial_rao,free_rao,held_netuid,alpha_units) VALUES(?,?,?,?,?)",
            (strategy, 100_000_000_000, 100_000_000_000, None, "0"),
        )
    incompatible = connection.execute(
        "SELECT strategy,initial_rao FROM portfolios WHERE initial_rao != ?",
        (100_000_000_000,),
    ).fetchall()
    if incompatible:
        connection.close()
        details = ", ".join(f"{row['strategy']}={row['initial_rao']} rao" for row in incompatible)
        raise RuntimeError(
            "database contains portfolios created with a different initial balance "
            f"({details}); preserve it as historical data and use a fresh database "
            "for the 100 TAO experiment"
        )
    connection.commit()
    return connection

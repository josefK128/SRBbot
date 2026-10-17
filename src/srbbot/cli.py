from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from .broker import CostModel
from .client import NoNewSnapshot, SRBClient, normalize_snapshot, validate_freshness
from .database import connect
from .engine import DuplicateSnapshot, Engine


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="srbbot")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "serve"):
        command = sub.add_parser(name)
        command.add_argument("--input", type=Path, help="read a saved snapshot instead of HTTPS")
        command.add_argument("--url", default=os.getenv("SRBBOT_SRB_URL"))
        command.add_argument("--db", default=os.getenv("SRBBOT_DB_PATH", "@data/srbbot.sqlite3"))
        command.add_argument(
            "--max-staleness-seconds",
            type=int,
            default=int(os.getenv("SRBBOT_MAX_STALENESS_SECONDS", "7200")),
        )
        if name == "serve":
            command.add_argument("--poll-seconds", type=int, default=120)
    return parser


def _costs() -> CostModel:
    return CostModel(
        stake_fee_bps=int(os.getenv("SRBBOT_STAKE_FEE_BPS", "5")),
        unstake_fee_bps=int(os.getenv("SRBBOT_UNSTAKE_FEE_BPS", "5")),
        slippage_bps=int(os.getenv("SRBBOT_SLIPPAGE_BPS", "25")),
        network_fee_rao=int(os.getenv("SRBBOT_NETWORK_FEE_RAO", "100000")),
    )


def _once(args: argparse.Namespace, engine: Engine, client: SRBClient | None = None) -> None:
    if args.input:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        snapshot = normalize_snapshot(payload)
    else:
        if not args.url:
            raise SystemExit("--url or SRBBOT_SRB_URL is required")
        client = client or SRBClient(
            args.url, service_token=os.getenv("SRBBOT_SITES_TOKEN") or None
        )
        snapshot, payload = client.fetch()
        validate_freshness(snapshot, args.max_staleness_seconds)
    decisions = engine.process(snapshot, payload)
    for decision in decisions:
        print(
            f"{snapshot.snapshot_id} {decision.strategy} {decision.action} "
            f"target={decision.candidate_netuid} reason={decision.reason}"
        )


def main() -> None:
    args = _parser().parse_args()
    engine = Engine(connect(args.db), _costs())
    if args.command == "run":
        _once(args, engine)
        return
    if not args.url:
        raise SystemExit("--url or SRBBOT_SRB_URL is required")
    client = SRBClient(args.url, service_token=os.getenv("SRBBOT_SITES_TOKEN") or None)
    catchup_url = os.getenv("SRBBOT_CATCHUP_URL")
    if not catchup_url and args.url.endswith("/api/srb/latest"):
        catchup_url = f"{args.url.removesuffix('/latest')}/since"
    catchup_client = (
        SRBClient(catchup_url, service_token=os.getenv("SRBBOT_SITES_TOKEN") or None)
        if catchup_url
        else None
    )
    while True:
        try:
            latest = engine.db.execute(
                "SELECT sampled_at FROM snapshots ORDER BY sampled_at DESC LIMIT 1"
            ).fetchone()
            if latest and catchup_client:
                batch = catchup_client.fetch_since(latest["sampled_at"])
                for snapshot, payload in batch:
                    engine.process(snapshot, payload)
                if batch:
                    validate_freshness(batch[-1][0], args.max_staleness_seconds)
            else:
                _once(args, engine, client)
        except (DuplicateSnapshot, NoNewSnapshot):
            pass
        time.sleep(args.poll_seconds)

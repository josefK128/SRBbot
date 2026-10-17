from __future__ import annotations

import argparse
import getpass
import tempfile
import time
from pathlib import Path

from srbbot.client import NoNewSnapshot, SRBClient, validate_freshness
from srbbot.database import connect
from srbbot.engine import Engine

DEFAULT_URL = "https://stake-rebalance-stage2.mark-rudolph.chatgpt.site/api/srb/latest"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Bounded real Stage2 polling E2E")
    result.add_argument("--url", default=DEFAULT_URL)
    result.add_argument("--wait-for-next", action="store_true")
    result.add_argument("--poll-seconds", type=int, default=120)
    result.add_argument("--timeout-seconds", type=int, default=5400)
    result.add_argument("--max-staleness-seconds", type=int, default=7200)
    return result


def main() -> int:
    args = parser().parse_args()
    token = getpass.getpass("Sites service token: ")
    if not token:
        raise SystemExit("A Sites service token is required.")
    client = SRBClient(args.url, service_token=token)
    with tempfile.TemporaryDirectory(prefix="srbbot-staging-e2e-") as directory:
        db = connect(Path(directory) / "e2e.sqlite3")
        engine = Engine(db)
        first, payload = client.fetch()
        validate_freshness(first, args.max_staleness_seconds)
        engine.process(first, payload)
        print(
            f"PASS current snapshot={first.snapshot_id} "
            f"sampled_at={first.sampled_at.isoformat()} subnets={len(first.observations)}"
        )

        try:
            client.fetch()
        except NoNewSnapshot:
            print("PASS unchanged poll returned HTTP 304")
        else:
            raise RuntimeError("unchanged poll did not return HTTP 304")

        expected_snapshots = 1
        if args.wait_for_next:
            deadline = time.monotonic() + args.timeout_seconds
            while time.monotonic() < deadline:
                time.sleep(args.poll_seconds)
                try:
                    next_snapshot, next_payload = client.fetch()
                except NoNewSnapshot:
                    continue
                validate_freshness(next_snapshot, args.max_staleness_seconds)
                engine.process(next_snapshot, next_payload)
                expected_snapshots = 2
                print(
                    f"PASS next snapshot={next_snapshot.snapshot_id} "
                    f"sampled_at={next_snapshot.sampled_at.isoformat()}"
                )
                break
            else:
                raise TimeoutError("no new Stage2 sample arrived before the E2E timeout")

        snapshots = db.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
        decisions = db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        nav_rows = db.execute("SELECT COUNT(*) FROM positions_nav").fetchone()[0]
        assert snapshots == expected_snapshots
        assert decisions == expected_snapshots * 2
        assert nav_rows == expected_snapshots * 2
        print(
            f"PASS database snapshots={snapshots} decisions={decisions} nav_rows={nav_rows}"
        )
    print("PASS temporary E2E database removed; long-duration run not started")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

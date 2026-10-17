from __future__ import annotations

import json
import threading
from copy import deepcopy
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

from srbbot.client import NoNewSnapshot, SRBClient, validate_freshness
from srbbot.database import connect
from srbbot.engine import Engine

TOKEN = "sites-service-test-token"


def sample() -> dict[str, object]:
    return {
        "snapshot_id": "retained-current",
        "sampled_at": "2026-10-10T16:00:00Z",
        "schema_version": "1",
        "tao_price_usd": "300",
        "subnets": [
            {"netuid": 1, "score": "80", "delta_price_1h": "0.02", "price_tao": "0.5"},
            {"netuid": 2, "score": "70", "delta_price_1h": "0.08", "price_tao": "1"},
        ],
    }


@pytest.mark.e2e
def test_authenticated_poll_etag_and_three_strategy_cycles(tmp_path):
    state = {"payload": sample(), "history": [sample()], "requests": 0}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            state["requests"] += 1
            parsed = urlparse(self.path)
            if parsed.path not in ("/api/srb/latest", "/api/srb/since"):
                self.send_error(404)
                return
            if self.headers.get("OAI-Sites-Authorization") != f"Bearer {TOKEN}":
                self.send_error(401)
                return
            if parsed.path == "/api/srb/since":
                after = parse_qs(parsed.query)["after"][0]
                after_time = datetime.fromisoformat(after.replace("Z", "+00:00"))
                snapshots = [
                    item
                    for item in state["history"]
                    if datetime.fromisoformat(item["sampled_at"].replace("Z", "+00:00"))
                    > after_time
                ]
                body = json.dumps(
                    {
                        "gap": False,
                        "has_more": False,
                        "retention_earliest": state["history"][0]["sampled_at"],
                        "snapshots": snapshots,
                    }
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            etag = f'"{state["payload"]["snapshot_id"]}"'
            if self.headers.get("If-None-Match") == etag:
                self.send_response(304)
                self.end_headers()
                return
            body = json.dumps(state["payload"]).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("ETag", etag)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/api/srb/latest"
    client = SRBClient(url, service_token=TOKEN)
    engine = Engine(connect(tmp_path / "polling.sqlite3"))

    try:
        denied = SRBClient(url, service_token="wrong-token")
        with pytest.raises(ValueError, match="401"):
            denied.fetch()

        first, first_payload = client.fetch()
        validate_freshness(first, max_age_seconds=10**10)
        engine.process(first, first_payload)

        with pytest.raises(NoNewSnapshot):
            client.fetch()

        state["payload"] = deepcopy(sample())
        state["payload"]["snapshot_id"] = "next-hour"
        state["payload"]["sampled_at"] = "2026-10-10T17:00:00Z"
        state["payload"]["tao_price_usd"] = "307"
        state["history"].append(state["payload"])
        catchup = SRBClient(
            f"http://127.0.0.1:{server.server_port}/api/srb/since",
            service_token=TOKEN,
        )
        [(second, second_payload)] = catchup.fetch_since(first.sampled_at.isoformat())
        engine.process(second, second_payload)
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert state["requests"] == 4
    assert engine.db.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 2
    assert engine.db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 6
    assert engine.db.execute("SELECT COUNT(*) FROM positions_nav").fetchone()[0] == 6
    market = engine.db.execute(
        "SELECT DISTINCT tao_market FROM positions_nav WHERE snapshot_id='next-hour'"
    ).fetchall()
    assert [row["tao_market"] for row in market] == [1]

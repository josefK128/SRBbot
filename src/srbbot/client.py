from __future__ import annotations

import hashlib
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from typing import Any

from .models import Observation, Snapshot, decimal, parse_time


class SnapshotError(ValueError):
    pass


class NoNewSnapshot(Exception):
    pass


class CatchupGap(SnapshotError):
    pass


def _required(mapping: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in mapping:
            return mapping[name]
    raise SnapshotError(f"missing required field: {' or '.join(names)}")


def normalize_snapshot(payload: dict[str, Any]) -> Snapshot:
    root = payload.get("data", payload)
    if not isinstance(root, dict):
        raise SnapshotError("snapshot root must be an object")
    sampled_raw = _required(root, "sampled_at", "source_time", "timestamp")
    records = _required(root, "subnets", "observations")
    if not isinstance(records, list) or not records:
        raise SnapshotError("subnets must be a non-empty list")
    observations: list[Observation] = []
    seen: set[int] = set()
    for record in records:
        if not isinstance(record, dict):
            raise SnapshotError("each subnet must be an object")
        try:
            netuid = int(_required(record, "netuid"))
            if netuid in seen:
                raise SnapshotError(f"duplicate netuid: {netuid}")
            seen.add(netuid)
            observations.append(
                Observation(
                    netuid=netuid,
                    score=decimal(_required(record, "score")),
                    delta_price_1h=decimal(_required(record, "delta_price_1h", "price_change_1h")),
                    price_tao=decimal(_required(record, "price_tao")),
                )
            )
        except (TypeError, ValueError) as exc:
            raise SnapshotError(f"invalid subnet record: {exc}") from exc
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    snapshot_id = str(root.get("snapshot_id") or hashlib.sha256(canonical).hexdigest())
    try:
        return Snapshot(
            snapshot_id=snapshot_id,
            sampled_at=parse_time(str(sampled_raw)),
            tao_price_usd=decimal(_required(root, "tao_price_usd")),
            observations=tuple(observations),
            schema_version=str(root.get("schema_version", "1")),
        )
    except (TypeError, ValueError) as exc:
        raise SnapshotError(str(exc)) from exc


class SRBClient:
    def __init__(
        self, url: str, service_token: str | None = None, timeout_seconds: float = 20
    ) -> None:
        is_local_test = url.startswith(("http://127.0.0.1", "http://localhost"))
        if not url.startswith("https://") and not is_local_test:
            raise ValueError("SRB endpoint must use HTTPS (except local tests)")
        self.url = url
        self.service_token = service_token
        self.timeout_seconds = timeout_seconds
        self.etag: str | None = None

    def fetch(self) -> tuple[Snapshot, dict[str, Any]]:
        headers = {"Accept": "application/json", "User-Agent": "SRBbot/0.1"}
        if self.service_token:
            headers["OAI-Sites-Authorization"] = f"Bearer {self.service_token}"
        if self.etag:
            headers["If-None-Match"] = self.etag
        request = urllib.request.Request(
            self.url,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
                context=ssl.create_default_context(),
            ) as response:
                if response.status != 200:
                    raise SnapshotError(f"unexpected HTTP status: {response.status}")
                payload = json.load(response)
                response_etag = response.headers.get("ETag")
        except urllib.error.HTTPError as exc:
            if exc.code == 304:
                raise NoNewSnapshot from exc
            raise SnapshotError(f"unexpected HTTP status: {exc.code}") from exc
        if not isinstance(payload, dict):
            raise SnapshotError("response must be a JSON object")
        snapshot = normalize_snapshot(payload)
        self.etag = response_etag or f'"{snapshot.snapshot_id}"'
        return snapshot, payload

    def fetch_since(self, after: str, limit: int = 212) -> list[tuple[Snapshot, dict[str, Any]]]:
        separator = "&" if "?" in self.url else "?"
        url = f"{self.url}{separator}{urllib.parse.urlencode({'after': after, 'limit': limit})}"
        headers = {"Accept": "application/json", "User-Agent": "SRBbot/0.1"}
        if self.service_token:
            headers["OAI-Sites-Authorization"] = f"Bearer {self.service_token}"
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=headers),
                timeout=self.timeout_seconds,
                context=ssl.create_default_context(),
            ) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as exc:
            raise SnapshotError(f"unexpected HTTP status: {exc.code}") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("snapshots"), list):
            raise SnapshotError("catch-up response must contain snapshots")
        if payload.get("gap"):
            raise CatchupGap(
                f"hourly history gap before retention floor {payload.get('retention_earliest')}"
            )
        if payload.get("has_more"):
            raise SnapshotError("catch-up page limit exceeded")
        result = []
        for item in payload["snapshots"]:
            if not isinstance(item, dict):
                raise SnapshotError("catch-up snapshot must be an object")
            result.append((normalize_snapshot(item), item))
        return result


def validate_freshness(snapshot: Snapshot, max_age_seconds: int) -> None:
    age = (datetime.now(UTC) - snapshot.sampled_at).total_seconds()
    if age < -300:
        raise SnapshotError("snapshot timestamp is in the future")
    if age > max_age_seconds:
        raise SnapshotError(f"snapshot is stale ({int(age)} seconds old)")

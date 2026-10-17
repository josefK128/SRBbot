from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    endpoint = os.getenv("SRBBOT_SRB_URL", "")
    checks.append(("Sites endpoint", endpoint.startswith("https://"), endpoint or "missing"))
    checks.append(
        (
            "Sites service token",
            bool(os.getenv("SRBBOT_SITES_TOKEN")),
            "configured"
            if os.getenv("SRBBOT_SITES_TOKEN")
            else "missing",
        )
    )
    db_path = Path(os.getenv("SRBBOT_DB_PATH", "@data/srbbot.sqlite3"))
    checks.append(("Fresh database", not db_path.exists(), str(db_path)))
    for label, passed, detail in checks:
        print(f"{'PASS' if passed else 'BLOCK'}  {label}: {detail}")
    blocked = sum(not passed for _, passed, _ in checks)
    print(f"\nPreflight: {blocked} blocking item(s). No connection was attempted.")
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())

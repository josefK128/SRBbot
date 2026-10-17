from __future__ import annotations

import getpass
import os
from pathlib import Path

ENDPOINT = "https://stake-rebalance-stage2.mark-rudolph.chatgpt.site/api/srb/latest"
CATCHUP_ENDPOINT = "https://stake-rebalance-stage2.mark-rudolph.chatgpt.site/api/srb/since"


def main() -> int:
    token = getpass.getpass("Sites service token: ")
    if not token:
        raise SystemExit("A Sites service token is required.")
    path = Path("@data/srbbot.env")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f"SRBBOT_SRB_URL={ENDPOINT}",
                f"SRBBOT_CATCHUP_URL={CATCHUP_ENDPOINT}",
                f"SRBBOT_SITES_TOKEN={token}",
                "SRBBOT_DB_PATH=@data/srbbot.sqlite3",
                "SRBBOT_MAX_STALENESS_SECONDS=7200",
                "",
            ]
        ),
        encoding="utf-8",
    )
    os.chmod(path, 0o600)
    print(f"Configured protected runtime file: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

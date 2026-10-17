# SRBbot

SRBbot is a deterministic, simulation-only paper-staking bot. It consumes an
hourly Sites Stage2 SRB snapshot over HTTPS and independently runs three K=1
strategies, each initialized with 100 TAO:

- `score`: hold the highest-scoring subnet; replace when a different subnet's
  score is more than 110% of the held subnet's current score.
- `breakout`: hold the subnet with the highest published 1-hour price delta;
  replace when its delta is greater than `max(110% of held delta, 0.01)`.
- `conditional`: apply the Breakout rule when the contemporaneous TAO price
  change is below -1% or above +1%, and apply the Score rule during static
  periods from -1% through +1%, inclusive. The initial sample uses Score because
  no prior TAO price exists.

The simulator has no wallet keys and cannot submit a chain transaction.

## Development setup

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

Process a saved snapshot:

```bash
srbbot run --input @tests/fixtures/snapshot-001.json
```

Fetch the private Sites endpoint once:

```bash
export SRBBOT_SRB_URL=https://stake-rebalance-stage2.mark-rudolph.chatgpt.site/api/srb/latest
export SRBBOT_SITES_TOKEN=replace-with-sites-service-token
srbbot run
```

Run continuously, polling for the next accepted hourly sample:

```bash
srbbot serve --poll-seconds 120
```

On restart, `serve` asks `/api/srb/since` for every retained hourly sample
after the newest local timestamp and processes them oldest-first. The catch-up
URL is inferred from `/api/srb/latest`, or it may be set explicitly with
`SRBBOT_CATCHUP_URL`. This allows the computer to sleep without losing samples,
provided it resumes within the server's retained-history window. A retention
gap fails closed instead of silently skipping data.

Run the non-connecting launch preflight first:

```bash
python scripts/preflight.py
```

By default SQLite state is written to `@data/srbbot.sqlite3`. Override this
with `SRBBOT_DB_PATH`. Optional paper costs are configured with
`SRBBOT_STAKE_FEE_BPS`, `SRBBOT_UNSTAKE_FEE_BPS`, and
`SRBBOT_SLIPPAGE_BPS`; the fixed network estimate is
`SRBBOT_NETWORK_FEE_RAO`. Frozen defaults are 5 basis points swap fee per
operation, 25 basis points price impact per operation, and 100,000 rao
(0.0001 TAO) network fee. The input contract is documented in
`docs/snapshot-contract.md`.

The client sends the Sites service token only in the
`OAI-Sites-Authorization` header. It retains the endpoint's ETag and sends
`If-None-Match` on later polls; HTTP 304 means there is no new sample. SQLite
snapshot and timestamp uniqueness provide a second exactly-once guard. Every
accepted sample requires positive `price_tao` for each subnet and stores the
derived `tao-market` marker (`-1`, `0`, `1`, or `null` for the first sample).

Run the authenticated polling integration test with:

```bash
pytest -m e2e
```

## Layout

- `src/srbbot/` - HTTPS client, validation, strategy engine, paper broker,
  SQLite journal, runner, and CLI
- `@tests/` - automated tests and sanitized fixtures
- `@data/` - WSL-local runtime database and logs (ignored by Git)
- `docs/` - interface contract and implementation notes

All monetary calculations use integer rao (`1 TAO = 1,000,000,000 rao`) and
all comparisons use `Decimal`; binary floats are not used for decisions or
ledger balances. Each hourly NAV record also stores an explicit percentage
return from the 100 TAO starting balance, so a 1 TAO gain or loss initially
corresponds to one percentage point.

The initial balance is an experiment invariant. A database containing a prior
10 TAO portfolio is rejected rather than silently rewriting its history; start
the 100 TAO experiment with a fresh database path.

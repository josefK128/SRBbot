# SRBbot launch checklist

The experiment is not started. Complete this checklist, run preflight, inspect
the first event, and obtain an explicit start instruction.

## Required from SRB

- `SRBBOT_SRB_URL`: the private Sites `/api/srb/latest` endpoint.
- `SRBBOT_CATCHUP_URL`: optional explicit `/api/srb/since` endpoint; it is
  inferred automatically when the latest URL uses the standard route.
- `SRBBOT_SITES_TOKEN`: a Sites service-access token stored only in the local
  ignored environment file.
- The endpoint returns the latest successfully committed complete sample.
- The response includes `ETag`; matching `If-None-Match` returns HTTP 304.

## Polling deployment

No relay, additional hostname, container host, or Internet Computer canister is
required. The single bot polls Sites every 120 seconds. HTTP 304 and local
database uniqueness make unchanged results inexpensive and safe. After sleep or
restart, the bot retrieves retained samples newer than its local checkpoint in
chronological order. It refuses to proceed if the server reports a retention
gap.

## Quote and valuation requirement

The frozen event contains selection data (`netuid`, `score`, and
`delta_price_1h`) plus `tao_price_usd`. It does not contain an executable subnet
price. Before launch, choose one:

1. Add `price_tao` to every subnet record in the SRB event; or
2. Configure and validate a Bittensor quote adapter that enriches every record
   before the atomic snapshot is accepted.

The quote adapter also needs the validator/hotkey target associated with each
subnet only if quotes are fetched from the chain. For the initial paper launch,
server-supplied `price_tao` is sufficient and validator/hotkey mapping is
deferred. No wallet key or wallet address is required for paper accounting.

## Exactly-once local processing

Each unique valid sample is committed as one SQLite transaction: one raw
snapshot plus the Score and Breakout observations, decisions, fills, and NAV
records. Snapshot ID and timestamp uniqueness prevent a replay from creating a
second decision cycle. The acknowledgement is `duplicate`, with no new write.

## End-to-end launch test

The local E2E starts an HTTP endpoint that enforces the Sites service header.
It rejects a bad token, returns a retained sample and ETag, returns HTTP 304 to
an unchanged poll, then returns a second unique sample. It verifies exactly two
snapshots, four decisions, four NAV rows, and the TAO-market classification.

```bash
pytest -m e2e
```

## Frozen costs

- Application swap fee: 5 basis points per stake or unstake.
- Modeled price impact: 25 basis points per stake or unstake.
- Network fee estimate: 100,000 rao (0.0001 TAO) per operation.
- Impermanent loss: zero.

## Commands

The preflight command does not connect to SRB:

```bash
source .venv/bin/activate
python scripts/preflight.py
```

Only after preflight passes and the user explicitly authorizes the start:

```bash
srbbot serve --poll-seconds 120
```

Never place secrets in `.env.example` or commit a populated `.env` file.

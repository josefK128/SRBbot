# Sites Stage2 SRB snapshot contract (v1)

SRBbot requires one coherent HTTPS JSON response per hourly SRB sample. Until a
real sanitized Sites response is supplied, this is the frozen adapter boundary:

```json
{
  "snapshot_id": "unique-hourly-id",
  "sampled_at": "2026-10-09T18:00:00Z",
  "schema_version": "1",
  "tao_price_usd": "350.25",
  "subnets": [
    {"netuid": 1, "score": "82.5", "delta_price_1h": "0.12", "price_tao": "0.0042"}
  ]
}
```

Sites returns this object from `GET /api/srb/latest`. The endpoint reads the
latest successfully committed sample and includes `price_tao` for every subnet;
selection values alone cannot produce paper fills or NAV.

`GET /api/srb/since?after=<ISO-8601>&limit=<n>` returns retained hourly
snapshots newer than the supplied timestamp, oldest-first. Its envelope also
reports `retention_earliest`, `latest_sampled_at`, `gap`, and `has_more`.
SRBbot fails closed on a retention gap or an incomplete page, ensuring a
sleeping client never silently treats missing hours as continuous history.

`price_change_1h` is accepted as an alias for `delta_price_1h`; `source_time`
or `timestamp` may alias `sampled_at`; and `observations` may alias `subnets`.
Values are parsed from their decimal string representation. Scores outside
`[0,100]`, missing fields, duplicate netuids, non-positive subnet prices,
duplicate snapshots, and time reversal fail closed. Live HTTPS responses also
fail when stale according to `SRBBOT_MAX_STALENESS_SECONDS`.

The delta unit must be confirmed against the real Sites response. The initial
strategy implements the brief literally: the breakout floor is `0.01` in the
same units as the published 1-hour delta.

## Delivery, authorization, and replay

SRBbot authenticates to the existing private Site using the service token in
`OAI-Sites-Authorization`. The endpoint returns an ETag derived from
`snapshot_id`; `If-None-Match` yields HTTP 304 while that sample remains current.
Each unique valid sample produces one atomic decision cycle containing one raw
snapshot and the Score and Breakout decision/NAV rows. Replays and repeated
polls produce no additional writes.

## Derived TAO market condition

For every accepted sample after the first, SRBbot computes
`P = (current_tao_price_usd - previous_tao_price_usd) / previous_tao_price_usd`
using decimal arithmetic. The derived JSON/ack property `tao-market` is `1`
when `P > 0.01`, `-1` when `P < -0.01`, and `0` for the inclusive interval
`[-0.01, 0.01]`. It is `null` for the first sample because no comparison exists.

The previous price, exact fractional change, and marker are stored on the
snapshot and duplicated onto the `score`, `breakout`, and `conditional` NAV
rows so later performance reports can group returns by the contemporaneous
market regime. Conditional applies the Breakout decision rule when the marker is
`-1` or `1` (falling or rising), and the Score rule when the marker is `0`
(static). The initial `null` condition uses Score. Conditional always operates
on its own independent holding.

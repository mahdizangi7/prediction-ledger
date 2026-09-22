# Prediction Market — GenLayer Intelligent Contract

A pari-mutuel YES/NO prediction market on BTC/ETH/SOL price thresholds,
built as a GenLayer Intelligent Contract, with a no-build HTML frontend.

```
contracts/prediction_market.py   Intelligent Contract (Python / GenVM)
frontend/index.html              Single-file dApp frontend (no build step)
scripts/time_probe.py            Diagnostic contract — checks which time
                                  API is deterministic on your pinned
                                  GenVM runtime (see below)
```

## 1. Deploy the contract

1. Open GenLayer Studio (local).
2. Create a new contract and paste `contracts/prediction_market.py`.
   Keep the first-line `# { "Depends": ... }` header as-is.
3. Deploy. Copy the resulting contract address — you'll need it in step 3.

### About `_now()`

`contracts/prediction_market.py` reads time via
`datetime.datetime.now(datetime.timezone.utc).timestamp()`. This was
confirmed deterministic by deploying `scripts/time_probe.py` first,
calling `probe()`, then reading `get_result()` — all four candidate
time sources it tries either errored or agreed. If you're on a
different pinned `py-genlayer` version than the one in this repo's
`Depends` header, redeploy the probe and re-check before trusting
`_now()` as-is; a version that disagrees between validators will
show up as the transaction failing to reach consensus.

## 2. Serve the frontend

Don't open `frontend/index.html` via `file://` — MetaMask doesn't
inject into `file://` pages by default. Serve it locally instead:

```bash
cd frontend
python3 -m http.server 8080
# open http://localhost:8080/
```

## 3. Connect

1. In MetaMask, add your local Studio network manually (Settings →
   Networks → Add network manually): RPC URL and Chain ID must match
   whatever your local Studio instance actually uses — check Studio's
   own network/connect panel or your `docker-compose.yml`, don't
   assume a value.
2. Import a Studio test account (private key) into MetaMask so you
   have GEN to bet with.
3. In the app, click **Settings** and fill in:
   - Contract address (from step 1)
   - RPC URL (same as MetaMask's)
   - Chain ID (same as MetaMask's)
4. Click **Connect Wallet**.

## Known unverified assumptions

These were reasoned from `genlayer-js`'s public README/docs, not
confirmed against a live deploy. If something breaks, check these
first (both live in `frontend/index.html`, inside the block marked
`GenLayer client wrapper`):

- `writeContract({ ..., value })` — the field name for attaching GEN
  to a payable call. If `place_bet` throws an "unknown field" style
  error, this is the first thing to check against your installed
  `genlayer-js` version.
- `chains.localnet` as the right preset for local Studio. Settings →
  RPC URL / Chain ID override this if it's wrong for your setup.

Open the "Raw console" panel at the bottom of the page for every
request/response the frontend sends — paste its output when
debugging.

## Contract design notes

- Money is real GEN, escrowed by the contract in wei (`int`), never
  `float` — floats aren't supported in GenVM calldata and rot storage
  precision.
- `resolve_market` reaches consensus on the YES/NO **decision**, not
  the raw price, and reverts with `[TRANSIENT] TOO_CLOSE_TO_THRESHOLD`
  if price sits within a band of the threshold, rather than deadlocking.
- `resolution_source` is restricted to a CoinGecko URL prefix
  (`ALLOWED_SOURCE_PREFIXES` in the contract) so a market creator can't
  point resolution at a URL they control.
- `void_market` is a permissionless escape hatch: if a market sits
  unresolved `VOID_GRACE_SECONDS` past its deadline, anyone can void
  it and all stakers reclaim their principal via `claim`.

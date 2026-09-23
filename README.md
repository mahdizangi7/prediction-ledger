# Prediction Ledger × GenLayer

Prediction Ledger is a decentralized prediction-market application built with **GenLayer**.

Users can create markets for BTC, ETH, and SOL based on a specific price threshold and deadline, place YES/NO positions, and resolve expired markets using externally retrieved historical price evidence.

The project combines a real GenLayer smart contract with a web frontend to demonstrate how **non-deterministic external data can be verified and turned into deterministic on-chain market outcomes**.

---

## Live Demo

https://peridiction-ledger.vercel.app

## GitHub

https://github.com/mahdizangi7/prediction-ledger

## Network

GenLayer Studio / Studionet

**Chain ID:** `61999`

## Deployed Contract

```text
0x1C011f310166CB73aD36A9E02b33519D72c9f160
```

RPC:

```text
https://studio.genlayer.com/api
```

---

# Overview

Prediction Ledger allows a user to create a prediction market such as:

> Will Bitcoin (BTC) be above $120,000 at the market deadline?

Each market contains:

* Asset
* Coin ID
* Price threshold
* Deadline
* Generated market question
* YES pool
* NO pool
* Market status
* Resolution outcome
* Resolution evidence
* Verification status

The important part of the design is that the market's question and settlement logic are derived from values stored by the smart contract.

This prevents the frontend from defining a different question from the one actually used during settlement.

---

# Why GenLayer?

Traditional smart contracts cannot directly retrieve arbitrary external web data.

Prediction markets, however, often depend on real-world information.

For example:

```text
Will BTC be above $120,000 at the deadline?
```

The contract needs an external source to determine the historical BTC price around the exact deadline.

Prediction Ledger uses GenLayer's non-deterministic execution model to retrieve external evidence and have validators independently verify the result.

The resolution flow therefore becomes:

```text
Market
   ↓
Stored deadline
   ↓
Historical external data source
   ↓
Leader retrieves evidence
   ↓
Validators independently verify evidence
   ↓
Consensus
   ↓
YES / NO outcome
   ↓
Persisted resolution evidence
```

---

# Core Features

## 1. Market Creation

Users can create a new prediction market by specifying:

* Asset
* Price threshold
* Deadline

Supported assets:

```text
BTC
ETH
SOL
```

The contract maps each asset to its corresponding CoinGecko identifier.

```text
BTC → bitcoin
ETH → ethereum
SOL → solana
```

The market question is generated directly by the contract.

For example:

```text
Will Bitcoin (BTC) be above $120000 at the market deadline?
```

This ensures that the displayed question corresponds to the actual settlement rule.

---

# 2. YES / NO Positions

Users can place a position on either:

```text
YES
NO
```

The bet amount is transferred through the payable contract method.

Each user's position is tracked independently for each market.

The contract stores:

* YES amount
* NO amount
* User position
* Market pools

---

# 3. Deadline-Based Betting Lock

Markets are only open for betting before their deadline.

Once:

```text
current_time >= deadline
```

the market can no longer accept new positions.

The frontend also disables the betting interface after the deadline.

This includes:

* YES
* NO
* Buy/Sell controls
* Bet amount
* Place Bet

The contract independently enforces the deadline as well, so the frontend is not the security boundary.

---

# 4. Independent Market Countdown

Every market card has its own countdown.

The frontend continuously calculates:

```text
deadline - current_time
```

and displays the remaining time.

When a market expires, its betting controls become locked and the market becomes eligible for resolution.

This is handled separately for each market rather than using one global countdown for all markets.

---

# 5. Historical Price Resolution

The resolution mechanism does not simply query the current cryptocurrency price.

Instead, it constructs a historical CoinGecko API request based on the **stored market deadline**.

The evidence source follows the structure:

```text
https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range
```

The requested range covers approximately:

```text
deadline - 24 hours
```

to:

```text
deadline + 24 hours
```

The contract then searches the returned historical observations and selects the observation closest to the stored deadline.

---

# 6. Evidence Is Bound to the Market Deadline

A key part of the resolution architecture is that the external evidence is not arbitrary.

The contract stores:

```text
asset
coin_id
threshold
deadline
source
```

During resolution, the contract reconstructs the expected source from the stored values.

The resolution process checks that the source corresponds to the market's:

* Asset
* Coin ID
* Deadline

This prevents the resolution process from silently switching to an unrelated asset or time period.

---

# 7. Observation-Time Validation

The selected historical observation contains:

```text
price
observed_at
distance_seconds
```

The contract verifies that the observation is sufficiently close to the market deadline.

The current maximum allowed distance is:

```text
3600 seconds
```

or approximately one hour.

Therefore, a historical observation that is too far away from the deadline cannot be accepted as valid settlement evidence.

---

# 8. Validator-Based Verification

The leader retrieves the historical data.

Validators do not simply trust the leader's final YES/NO answer.

Instead, validators independently:

1. Check the stored market parameters.
2. Check the asset.
3. Check the CoinGecko coin ID.
4. Check the deadline.
5. Check the expected source.
6. Retrieve the external historical data.
7. Extract their own closest observation.
8. Check the observation timestamp.
9. Compare the observed price.
10. Independently calculate the YES/NO outcome.

The validator therefore verifies the **evidence behind the outcome**, rather than merely verifying that the leader returned an allowed label.

Conceptually:

```text
Leader
  │
  ├── external historical data
  ├── observed price
  ├── observation timestamp
  └── calculated outcome
          │
          ▼
      Validators
          │
          ├── independently fetch data
          ├── independently find observation
          ├── verify timestamp
          ├── verify price
          └── independently calculate outcome
                  │
                  ▼
               Consensus
```

---

# 9. Price Tolerance

Because external historical APIs can expose slightly different numeric representations, the contract uses a small price tolerance when comparing independently retrieved observations.

The configured tolerance is:

```text
0.2%
```

with a minimum absolute tolerance of:

```text
$0.50
```

This is used to compare independently retrieved evidence while still requiring the observations to represent essentially the same historical market price.

---

# 10. Deterministic Outcome Rule

The settlement rule itself is intentionally simple.

For a market with:

```text
price > threshold
```

the outcome is:

```text
YES
```

Otherwise:

```text
NO
```

The same rule is used by the leader and validators.

Example:

```text
Threshold: $120,000
Observed price: $121,500

121,500 > 120,000

Outcome: YES
```

---

# 11. Persisted Resolution Evidence

After successful consensus, the contract stores the resolution evidence.

The persisted evidence includes information such as:

```text
asset
coin_id
deadline
source
observed_at
price
distance_seconds
outcome
```

The frontend can retrieve this evidence and display it in the market detail view.

This provides a provenance trail connecting:

```text
Market
→ Deadline
→ External source
→ Historical observation
→ Price
→ Outcome
```

---

# 12. Market Status

Markets move through a simple lifecycle:

```text
OPEN
  ↓
Deadline reached
  ↓
RESOLUTION
  ↓
RESOLVED
```

A resolved market contains its final:

* Outcome
* Verification state
* Resolution timestamp
* Historical evidence

---

# 13. Claiming Winnings

After a market has been successfully resolved and verified, users holding the winning position can claim their proportional payout.

The payout is calculated from the winning pool and the user's winning position.

The contract also records whether a user has already claimed.

This prevents the same position from being claimed more than once.

---

# Smart Contract

The main contract is implemented in:

```text
contract.py
```

The contract exposes the following main methods.

## Write Methods

### `create_market`

Creates a new prediction market.

Parameters:

```text
asset
threshold
deadline
```

---

### `place_bet`

Places a YES or NO position.

Parameters:

```text
market_id
side
```

The payment amount is supplied through the payable transaction value.

---

### `resolve_market`

Resolves an expired market.

The method:

1. Loads the stored market.
2. Verifies that the deadline has passed.
3. Builds the expected historical evidence source.
4. Retrieves historical price data.
5. Selects the observation closest to the deadline.
6. Calculates the outcome.
7. Runs validator verification.
8. Stores the final resolution evidence.

---

### `claim`

Allows a winner to claim their payout after successful resolution.

---

## Read Methods

### `get_market`

Returns the complete market state.

### `get_position`

Returns a user's position in a specific market.

### `has_claimed`

Checks whether a user has already claimed winnings.

### `get_counter`

Returns the current market counter.

### `get_latest_id`

Returns the latest market ID.

### `list_markets`

Returns the available market IDs.

### `get_odds`

Returns the current YES/NO market distribution.

### `get_resolution_evidence`

Returns the persisted evidence used during resolution.

---

# Storage Architecture

The contract maintains persistent state for:

```text
counter
markets
positions
claims
market_ids
```

Markets and user positions are stored using GenLayer persistent storage structures.

Each market stores the data necessary to reproduce and verify its settlement conditions.

---

# Frontend

The frontend is implemented as a lightweight static web application.

The current frontend is intentionally simple and does not require a traditional backend server.

It provides:

* Wallet connection
* Market list
* Market creation
* Market cards
* Individual market countdowns
* YES/NO selection
* Bet amount
* Position information
* Market odds
* Resolution controls
* Historical price chart
* Resolution evidence
* Claim interface
* Responsive layout

---

# Market Charts

Each market displays a chart corresponding to its underlying asset.

For example:

```text
BTC Market → BTC price chart
ETH Market → ETH price chart
SOL Market → SOL price chart
```

For active markets, the frontend displays recent market-price information.

For expired or resolved markets, the chart can show historical information around the market deadline and the threshold used by the prediction.

This makes it easier to visually understand the relationship between:

```text
Price
Threshold
Deadline
Outcome
```

---

# Frontend Configuration

The frontend uses a fixed GenLayer configuration.

```javascript
const FIXED_CONFIG = Object.freeze({
  address: "0x1C011f310166CB73aD36A9E02b33519D72c9f160",
  rpc: "https://studio.genlayer.com/api",
  chainId: "61999"
});
```

The contract address is therefore not dependent on users entering configuration values manually.

---

# Technology Stack

## Smart Contract

* Python
* GenLayer
* GenLayer non-deterministic execution
* GenLayer validator consensus
* Persistent contract storage

## External Data

* CoinGecko historical market data API

## Frontend

* HTML
* CSS
* JavaScript
* Canvas-based charts
* `genlayer-js`

## Deployment

* GenLayer Studio / Studionet
* Vercel

---

# Security and Architecture Considerations

Prediction markets depend heavily on correct settlement data.

Prediction Ledger therefore separates several responsibilities:

### Contract State

The contract stores the market's actual:

```text
asset
threshold
deadline
```

### Evidence Source

The historical source is constructed from those stored values.

### Leader

The leader retrieves external data and proposes the resolution evidence.

### Validators

Validators independently retrieve and verify the evidence.

### Consensus

The result is only persisted after the GenLayer nondeterministic execution reaches the required consensus.

### Frontend

The frontend provides usability and visualization but does not determine the final market outcome.

This means that changing frontend text cannot change the contract's settlement rule.

---

# Example Market

Suppose a user creates:

```text
Asset:
BTC

Threshold:
$120,000

Deadline:
Market-specific timestamp
```

The contract generates:

```text
Will Bitcoin (BTC) be above $120000 at the market deadline?
```

When the deadline passes, the contract retrieves historical BTC price observations around that exact deadline.

Suppose the closest valid observation is:

```text
Observed price:
$121,500
```

The contract evaluates:

```text
121,500 > 120,000
```

Therefore:

```text
YES
```

The validators independently verify the evidence and outcome.

After successful consensus, the contract stores the resolution evidence on-chain.

---

# Resolution Flow

The complete settlement path is:

```text
1. User creates market
        ↓
2. Contract stores asset / threshold / deadline
        ↓
3. Contract generates question
        ↓
4. Users place YES / NO positions
        ↓
5. Deadline passes
        ↓
6. Betting becomes locked
        ↓
7. resolve_market() is called
        ↓
8. Contract reconstructs historical source
        ↓
9. Leader retrieves historical data
        ↓
10. Closest observation to deadline is selected
        ↓
11. Leader calculates YES / NO
        ↓
12. Validators independently retrieve evidence
        ↓
13. Validators verify timestamp and price
        ↓
14. Validators independently calculate outcome
        ↓
15. GenLayer reaches consensus
        ↓
16. Resolution evidence is persisted
        ↓
17. Winning users can claim
```

---

# Milestone / New Progress

Prediction Ledger has evolved beyond the initial prediction-market implementation.

The current version introduces a substantially more verifiable settlement architecture.

The main improvements include:

### Deadline-bound resolution

Resolution evidence is tied to the market's stored deadline rather than relying on a generic current-price query.

### Historical evidence

The contract retrieves historical market observations around the relevant settlement time.

### Observation validation

Validators check not only the outcome but also the observation timestamp and price.

### Contract-bound market questions

The displayed market question is generated from the same asset and threshold stored by the contract.

### Persistent provenance

Resolution evidence is persisted so that the frontend can display how the final outcome was determined.

### New deployment

The updated contract is deployed on GenLayer with the current address:

```text
0x1C011f310166CB73aD36A9E02b33519D72c9f160
```

### Improved frontend

The frontend now includes independent market countdowns, deadline-based betting locks, per-market asset charts, and resolution evidence visualization.

These changes make the project more than a basic prediction-market interface: the focus is now on **verifiable, deadline-bound, externally sourced market settlement using GenLayer's validator model**.

---

# Running the Frontend Locally

Clone the repository:

```bash
git clone https://github.com/mahdizangi7/prediction-ledger.git
```

Enter the frontend directory:

```bash
cd prediction-ledger
```

The frontend is a static application and can be served with any simple local HTTP server.

For example:

```bash
npx serve .
```

Then open the local address shown by the server.

---

# Deployment

The production frontend is deployed through Vercel.

Typical deployment command:

```bash
npx vercel --prod
```

The deployed application is:

```text
https://peridiction-ledger.vercel.app
```

---

# Project Structure

```text
prediction-ledger/
│
├── contract.py
├── index.html
└── README.md
```

The exact repository structure may contain additional project files depending on the deployment environment.

---

# Current Contract

```text
Network: GenLayer Studio / Studionet
Chain ID: 61999

Contract:
0x1C011f310166CB73aD36A9E02b33519D72c9f160

RPC:
https://studio.genlayer.com/api
```

---

# Status

Prediction Ledger currently demonstrates:

* [x] GenLayer smart contract
* [x] Real deployed contract
* [x] BTC / ETH / SOL markets
* [x] Contract-generated market questions
* [x] YES / NO positions
* [x] Payable betting
* [x] Deadline enforcement
* [x] Independent market countdowns
* [x] Historical external price evidence
* [x] Deadline-bound evidence
* [x] Validator-based evidence verification
* [x] Observation timestamp verification
* [x] Price verification
* [x] Deterministic YES / NO settlement rule
* [x] Persisted resolution evidence
* [x] Claim functionality
* [x] Per-market price charts
* [x] Responsive frontend
* [x] Vercel deployment

---

# Conclusion

Prediction Ledger demonstrates how GenLayer can be used to build prediction markets whose settlement depends on real-world information.

Instead of treating an external API response as unquestioned truth, the application creates a verifiable resolution path:

```text
Stored Market Conditions
        ↓
Historical External Evidence
        ↓
Leader Retrieval
        ↓
Independent Validator Retrieval
        ↓
Evidence Verification
        ↓
Consensus
        ↓
On-chain Resolution
```

The result is a prediction-market architecture where the **market definition, settlement deadline, external evidence, validator verification, and final outcome are connected throughout the resolution process**.

---

## License

This project is provided for demonstration and development purposes.

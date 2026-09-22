# Prediction Ledger

Prediction Ledger is a decentralized prediction-market application built with **GenLayer Intelligent Contracts**.

The project allows users to create and participate in prediction markets around real-world asset prices. Market outcomes are resolved through GenLayer's consensus mechanism rather than relying on a single centralized resolver.

The current implementation focuses on BTC, ETH, and SOL price predictions and demonstrates how an on-chain prediction market can combine smart-contract state, user positions, and decentralized real-world resolution.

## Live Demo

https://peridiction-ledger.vercel.app

## GitHub

https://github.com/mahdizangi7/prediction-ledger

---

## What It Does

Prediction Ledger provides a simple workflow:

1. A prediction market is created with:

   * A question
   * An underlying asset
   * A target price
   * A resolution source
   * A deadline

2. Users choose **YES** or **NO** and place a prediction.

3. The contract stores:

   * Market metadata
   * YES pool
   * NO pool
   * Total pool
   * User positions
   * Market status

4. After the market deadline, the market can be resolved.

5. GenLayer validators independently retrieve the specified real-world information and participate in consensus over the result.

6. The resolved outcome is stored in the Intelligent Contract state.

This creates a reusable primitive for applications that need decentralized verification of real-world events.

---

## Example Markets

The current frontend is designed around three example markets:

* **Will Bitcoin (BTC) be above $120,000 in one week?**
* **Will Ethereum (ETH) be above $5,000 in one week?**
* **Will Solana (SOL) be above $250 in one week?**

The frontend can display market information, current pools, odds, and the connected user's position.

---

## Why GenLayer?

Traditional smart contracts cannot directly access arbitrary real-world information.

Prediction markets need an external source of truth because their final outcome depends on information that exists outside the blockchain.

Prediction Ledger uses GenLayer's Intelligent Contract architecture to make the resolution process part of the decentralized execution model.

Instead of trusting one backend server to determine the result, the contract can use GenLayer's validator consensus to independently evaluate the external information.

This makes the project useful as a building block for:

* Prediction markets
* Event-based applications
* Real-world settlement
* Oracle-like verification primitives
* Autonomous applications requiring external information

---

# Architecture

```text
┌─────────────────────────────┐
│        User Interface       │
│       frontend/index.html   │
└──────────────┬──────────────┘
               │
               │ genlayer-js
               ▼
┌─────────────────────────────┐
│     GenLayer Studionet      │
│                             │
│ PredictionMarket Contract   │
└──────────────┬──────────────┘
               │
               │ Consensus Resolution
               ▼
┌─────────────────────────────┐
│     GenLayer Validators     │
│                             │
│ Independent external-data   │
│ retrieval + verification    │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│       Real-world source     │
│                             │
│      CoinGecko API          │
└─────────────────────────────┘
```

---

# Smart Contract

The main Intelligent Contract is:

```text
contracts/prediction_market.py
```

The contract implements the core prediction-market state and operations.

## Main State

The contract maintains:

* A market counter
* Market records
* User positions
* Market status
* YES and NO pools
* Resolution information

Market information is serialized into contract state so it can be retrieved by the frontend.

---

# Contract Methods

The contract exposes methods for the complete market lifecycle.

### `create_market`

Creates a new prediction market.

Conceptually:

```text
create_market(
    question,
    asset,
    threshold,
    resolution_source,
    deadline
)
```

The market records the question, asset, target threshold, external resolution source, creator, deadline, and initial state.

---

### `place_bet`

Places a YES or NO prediction on an open market.

Conceptually:

```text
place_bet(
    market_id,
    side,
    amount
)
```

The contract updates both the global market pools and the user's position.

Supported sides:

```text
YES
NO
```

---

### `get_market`

Returns the stored information for a specific market.

This is used by the frontend to display the market state.

---

### `get_position`

Returns the current user's position for a market.

The position contains the user's YES/NO exposure and total amount.

---

### `get_odds`

Calculates the current market distribution based on the YES and NO pools.

This allows the frontend to present the current market probabilities/odds.

---

### `resolve_market`

Attempts to resolve a market after its deadline.

The resolution process uses GenLayer's nondeterministic execution and validator consensus to retrieve and verify the external information required to determine the outcome.

---

### `get_latest_id`

Returns the latest market identifier.

This is used by the frontend when discovering available markets.

---

# Consensus-Based Resolution

The most important part of Prediction Ledger is the resolution mechanism.

A prediction market cannot rely only on information supplied by the user because the user may have an incentive to provide incorrect information.

The contract therefore uses GenLayer's consensus capabilities.

The resolution process conceptually follows:

```text
Market reaches deadline
        │
        ▼
Resolve request
        │
        ▼
Leader retrieves external evidence
        │
        ▼
Validators independently verify
the relevant asset and outcome
        │
        ▼
Consensus
        │
        ▼
Outcome stored on-chain
```

For cryptocurrency markets, the resolution source is based on CoinGecko's price data.

The intended resolution question is equivalent to:

```text
Was the specified asset above the specified
threshold when the market reached its deadline?
```

The contract does not simply trust the frontend's displayed price.

---

# Validation Logic

The resolution logic is designed to validate the substantive result rather than merely accepting an arbitrary value.

Validators check the relevant:

* Asset
* Target threshold
* External data
* Reported outcome
* Price consistency

The contract uses a tolerance for comparing independently retrieved market prices so that small differences between data retrievals do not unnecessarily cause disagreement.

The goal is to make the consensus result robust to normal differences in external API responses while still rejecting materially inconsistent evidence.

---

# Supported Assets

The current application focuses on:

| Symbol | Asset    |
| ------ | -------- |
| BTC    | Bitcoin  |
| ETH    | Ethereum |
| SOL    | Solana   |

The frontend also uses CoinGecko asset identifiers to obtain current market information.

---

# Frontend

The frontend is implemented as a lightweight single-page application:

```text
frontend/index.html
```

It uses:

* HTML
* CSS
* JavaScript
* `genlayer-js`

The GenLayer JavaScript SDK is loaded through jsDelivr.

The current implementation uses:

```text
genlayer-js 1.1.8
```

The frontend provides:

* Wallet connection
* Market discovery
* Market creation
* YES/NO prediction placement
* User position display
* Market odds
* Market status
* Market resolution
* Cryptocurrency price display

---

# Network Configuration

The current deployed contract is on **GenLayer Studionet**.

```text
Network: GenLayer Studionet
Chain ID: 61999
RPC: https://studio.genlayer.com/api
```

Current contract:

```text
0x97eCfbE5b74ABd4848B083b4EBf1443626c4c107
```

The production frontend is intended to use these values directly rather than requiring users to manually configure the contract address or RPC.

---

# Local Development

Clone the repository:

```bash
git clone https://github.com/mahdizangi7/prediction-ledger.git
```

Enter the project:

```bash
cd prediction-ledger
```

The frontend is contained in:

```text
frontend/
```

Run a local static server from the frontend directory.

For example:

```bash
cd frontend
npx serve .
```

Then open the local URL shown by the server.

---

# Project Structure

```text
prediction-ledger/
│
├── contracts/
│   └── prediction_market.py
│
├── frontend/
│   ├── index.html
│   └── .gitignore
│
├── scripts/
│   └── time_probe.py
│
├── .gitignore
└── README.md
```

---

# Contract Deployment

The Intelligent Contract is deployed through **GenLayer Studio**.

The contract source is:

```text
contracts/prediction_market.py
```

After deployment, the resulting contract address is configured in the frontend.

Current deployment:

```text
0x97eCfbE5b74ABd4848B083b4EBf1443626c4c107
```

---

# Security and Trust Model

Prediction Ledger separates three different responsibilities:

### 1. Frontend

The frontend provides the user interface and submits transactions.

It is not the source of truth for the final market outcome.

### 2. Smart Contract

The Intelligent Contract stores market state and user positions and controls the market lifecycle.

### 3. GenLayer Consensus

External information used for settlement is evaluated through GenLayer's validator consensus.

This separation reduces reliance on a centralized application backend.

---

# Limitations

This project is an experimental prediction-market implementation.

Important limitations include:

* The current deployment uses GenLayer Studionet.
* External data depends on the availability of the selected data source.
* Cryptocurrency prices can differ slightly between data providers.
* The current market examples focus on BTC, ETH, and SOL.
* Production economic mechanisms such as sophisticated liquidity incentives, dispute markets, and advanced payout accounting can be extended in future versions.

---

# Future Extensions

Potential extensions include:

* More supported assets
* More external data providers
* Multi-source evidence verification
* Event-based markets beyond cryptocurrency
* More sophisticated payout mechanisms
* Market liquidity mechanisms
* Historical market analytics
* Market creation permissions
* Dispute and challenge mechanisms
* Additional validator consistency checks
* Automated market lifecycle management

---

# Design Goal

Prediction Ledger is intended to demonstrate a reusable GenLayer primitive:

> **A prediction market whose real-world outcome can be determined through decentralized consensus rather than a single centralized oracle.**

The project focuses on combining:

```text
On-chain state
+
Real-world data
+
GenLayer consensus
+
User predictions
=
Decentralized real-world settlement
```

---

# License

This repository is provided for experimentation, education, and development around GenLayer Intelligent Contracts.

# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

# PredictionMarket - pari-mutuel YES/NO markets on a USD price threshold.
#
# Money is real GEN held in escrow by this contract, in wei, as int.
# No floats touch storage or calldata.

from genlayer import *

import json
import datetime


# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------

# Anyone can create a market, so the resolution source must be pinned to
# hosts the contract trusts. Without this the market creator can point at
# a URL they control and mint whatever outcome they like.
ALLOWED_SOURCE_PREFIXES = (
    "https://api.coingecko.com/api/v3/simple/price",
)

COIN_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
}

# Resolution band. If the price lands within this distance of the
# threshold, the round returns UNRESOLVED instead of a coin flip.
# Leader and validator fetch seconds apart; without a band a price
# sitting on the threshold deadlocks the market forever.
BAND_RATIO = 0.005          # 0.5% of threshold
BAND_MIN_USD = 1.0

# After this much time past the deadline with no resolution, anyone can
# void the market and everyone claims their stake back. Funds must never
# be able to stay locked.
VOID_GRACE_SECONDS = 7 * 24 * 60 * 60

MAX_QUESTION_LEN = 500
MIN_QUESTION_LEN = 5


# Transfers to an EOA through get_contract_at move zero wei silently.
# Going through an evm contract interface is the form that actually pays.
@gl.evm.contract_interface
class _Payee:
    class View:
        pass

    class Write:
        pass


# ---------------------------------------------------------------------
# PURE HELPERS  (module level on purpose)
#
# These are called from inside the non-deterministic closures. They must
# not touch self: storage is inaccessible from non-deterministic blocks,
# and a bound method drags the contract object into the sandbox.
# ---------------------------------------------------------------------


def _extract_price(raw_text: str, coin_id: str) -> float:
    data = json.loads(raw_text)

    if coin_id not in data:
        raise gl.vm.UserError("[EXTERNAL] ASSET_MISSING")

    entry = data[coin_id]

    if "usd" not in entry:
        raise gl.vm.UserError("[EXTERNAL] USD_MISSING")

    price = float(entry["usd"])

    if price <= 0:
        raise gl.vm.UserError("[EXTERNAL] INVALID_PRICE")

    return price


def _classify(price: float, threshold: float) -> str:
    band = max(BAND_MIN_USD, threshold * BAND_RATIO)

    if abs(price - threshold) <= band:
        return "UNRESOLVED"

    return "YES" if price > threshold else "NO"


# ---------------------------------------------------------------------


class PredictionMarket(gl.Contract):
    counter: u256
    markets: TreeMap[str, str]
    positions: TreeMap[str, str]
    claimed: TreeMap[str, bool]
    market_ids: DynArray[str]

    def __init__(self):
        self.counter = u256(0)

    # =================================================================
    # KEYS / TIME
    # =================================================================

    def _market_key(self, market_id: str) -> str:
        return "market:" + str(market_id)

    def _position_key(self, market_id: str, user: str) -> str:
        return "position:" + str(market_id) + ":" + str(user).strip().lower()

    def _claim_key(self, market_id: str, user: str) -> str:
        return "claim:" + str(market_id) + ":" + str(user).strip().lower()

    def _now(self) -> int:
        # THE most version-sensitive line in this file. Run time_probe.py
        # against your pinned runtime and swap this body for whichever
        # candidate reported a sane value on every validator.
        return int(datetime.datetime.now(datetime.timezone.utc).timestamp())

    def _sender(self) -> str:
        return gl.message.sender_address.as_hex.lower()

    # =================================================================
    # STORAGE
    # =================================================================

    def _read_market(self, market_id: str):
        key = self._market_key(market_id)

        if key not in self.markets:
            raise gl.vm.UserError("[EXPECTED] MARKET_NOT_FOUND")

        return json.loads(self.markets[key])

    def _save_market(self, market) -> None:
        key = self._market_key(market["id"])
        self.markets[key] = json.dumps(market, sort_keys=True, separators=(",", ":"))

    def _read_position(self, market_id: str, user: str):
        key = self._position_key(market_id, user)

        if key not in self.positions:
            return {
                "market_id": str(market_id),
                "user": str(user).strip().lower(),
                "yes": "0",
                "no": "0",
            }

        return json.loads(self.positions[key])

    def _save_position(self, position) -> None:
        key = self._position_key(position["market_id"], position["user"])
        self.positions[key] = json.dumps(
            position, sort_keys=True, separators=(",", ":")
        )

    # =================================================================
    # VALIDATION
    # =================================================================

    def _validate_asset(self, asset: str) -> str:
        symbol = str(asset).upper().strip()

        if symbol not in COIN_IDS:
            raise gl.vm.UserError("[EXPECTED] UNSUPPORTED_ASSET")

        return symbol

    def _validate_source(self, source: str) -> str:
        url = str(source).strip()

        for prefix in ALLOWED_SOURCE_PREFIXES:
            if url.startswith(prefix):
                return url

        raise gl.vm.UserError("[EXPECTED] SOURCE_NOT_ALLOWED")

    def _pay(self, to_address: str, amount: int) -> None:
        if amount <= 0:
            return

        _Payee(Address(to_address)).emit_transfer(value=u256(amount))

    # =================================================================
    # CREATE
    # =================================================================

    @gl.public.write
    def create_market(
        self,
        question: str,
        asset: str,
        threshold: str,
        deadline: str,
        resolution_source: str,
    ) -> str:
        text = str(question).strip()

        if len(text) < MIN_QUESTION_LEN or len(text) > MAX_QUESTION_LEN:
            raise gl.vm.UserError("[EXPECTED] BAD_QUESTION_LENGTH")

        symbol = self._validate_asset(asset)
        source = self._validate_source(resolution_source)

        try:
            threshold_value = float(str(threshold))
        except Exception:
            raise gl.vm.UserError("[EXPECTED] BAD_THRESHOLD")

        if threshold_value <= 0:
            raise gl.vm.UserError("[EXPECTED] BAD_THRESHOLD")

        try:
            deadline_value = int(str(deadline))
        except Exception:
            raise gl.vm.UserError("[EXPECTED] BAD_DEADLINE")

        now = self._now()

        if deadline_value <= now:
            raise gl.vm.UserError("[EXPECTED] DEADLINE_IN_PAST")

        self.counter = u256(int(self.counter) + 1)
        market_id = str(int(self.counter))

        market = {
            "id": market_id,
            "question": text,
            "asset": symbol,
            "coin_id": COIN_IDS[symbol],
            "threshold": repr(threshold_value),
            "deadline": str(deadline_value),
            "void_after": str(deadline_value + VOID_GRACE_SECONDS),
            "resolution_source": source,
            "creator": self._sender(),
            "status": "open",
            "yes_pool": "0",
            "no_pool": "0",
            "resolved_price": "",
            "outcome": "",
            "resolved_at": "",
            "resolved_by": "",
            "created_at": str(now),
        }

        self._save_market(market)
        self.market_ids.append(market_id)

        return json.dumps(market, sort_keys=True, separators=(",", ":"))

    # =================================================================
    # BET  (real value, escrowed by this contract)
    # =================================================================

    @gl.public.write.payable
    def place_bet(self, market_id: str, side: str) -> str:
        amount = int(gl.message.value)

        if amount <= 0:
            raise gl.vm.UserError("[EXPECTED] ZERO_VALUE")

        market = self._read_market(market_id)

        if market["status"] != "open":
            raise gl.vm.UserError("[EXPECTED] MARKET_NOT_OPEN")

        if self._now() >= int(market["deadline"]):
            raise gl.vm.UserError("[EXPECTED] DEADLINE_PASSED")

        chosen = str(side).strip().upper()

        if chosen != "YES" and chosen != "NO":
            raise gl.vm.UserError("[EXPECTED] BAD_SIDE")

        user = self._sender()
        position = self._read_position(market_id, user)

        if chosen == "YES":
            position["yes"] = str(int(position["yes"]) + amount)
            market["yes_pool"] = str(int(market["yes_pool"]) + amount)
        else:
            position["no"] = str(int(position["no"]) + amount)
            market["no_pool"] = str(int(market["no_pool"]) + amount)

        self._save_market(market)
        self._save_position(position)

        return json.dumps(
            {"market": market, "position": position},
            sort_keys=True,
            separators=(",", ":"),
        )

    # =================================================================
    # RESOLVE
    # =================================================================

    @gl.public.write
    def resolve_market(self, market_id: str) -> str:
        market = self._read_market(market_id)

        if market["status"] != "open":
            return json.dumps(market, sort_keys=True, separators=(",", ":"))

        if self._now() < int(market["deadline"]):
            raise gl.vm.UserError("[EXPECTED] BEFORE_DEADLINE")

        # Copy everything the closures need into plain locals. No self,
        # no storage handles cross the sandbox boundary.
        source = str(market["resolution_source"])
        coin_id = str(market["coin_id"])
        threshold = float(market["threshold"])

        # gl.nondet.* is spelled out literally inside each closure, in the
        # same scope as the function handed to run_nondet_unsafe. Hiding
        # the fetch in a helper method breaks genvm-lint's scope match.
        def leader_fn():
            raw = gl.nondet.web.render(source, mode="text")
            price = _extract_price(raw, coin_id)

            return {
                "coin_id": coin_id,
                "price": repr(price),
                "outcome": _classify(price, threshold),
            }

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False

            leader_data = leader_result.calldata

            if not isinstance(leader_data, dict):
                return False

            if leader_data.get("coin_id") != coin_id:
                return False

            raw = gl.nondet.web.render(source, mode="text")
            price = _extract_price(raw, coin_id)

            # Agree on the decision, not the number. Two nodes fetch
            # seconds apart and BTC does not hold still in between.
            return leader_data.get("outcome") == _classify(price, threshold)

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        if not isinstance(result, dict):
            raise gl.vm.UserError("[EXTERNAL] BAD_CONSENSUS_SHAPE")

        outcome = str(result.get("outcome", "")).upper()

        if outcome == "UNRESOLVED":
            # Price sat on the threshold. Revert so the market stays open
            # and anyone can retry later, rather than baking a coin flip in.
            raise gl.vm.UserError("[TRANSIENT] TOO_CLOSE_TO_THRESHOLD")

        if outcome != "YES" and outcome != "NO":
            raise gl.vm.UserError("[EXTERNAL] BAD_OUTCOME")

        market["status"] = "resolved"
        market["outcome"] = outcome
        market["resolved_price"] = str(result.get("price", ""))
        market["resolved_at"] = str(self._now())
        market["resolved_by"] = self._sender()

        self._save_market(market)

        return json.dumps(market, sort_keys=True, separators=(",", ":"))

    # =================================================================
    # VOID  (permissionless escape hatch)
    # =================================================================

    @gl.public.write
    def void_market(self, market_id: str) -> str:
        market = self._read_market(market_id)

        if market["status"] != "open":
            raise gl.vm.UserError("[EXPECTED] NOT_OPEN")

        if self._now() < int(market["void_after"]):
            raise gl.vm.UserError("[EXPECTED] GRACE_NOT_OVER")

        market["status"] = "void"
        self._save_market(market)

        return json.dumps(market, sort_keys=True, separators=(",", ":"))

    # =================================================================
    # CLAIM
    # =================================================================

    @gl.public.write
    def claim(self, market_id: str) -> str:
        market = self._read_market(market_id)
        user = self._sender()

        claim_key = self._claim_key(market_id, user)

        if claim_key in self.claimed:
            raise gl.vm.UserError("[EXPECTED] ALREADY_CLAIMED")

        position = self._read_position(market_id, user)

        yes_stake = int(position["yes"])
        no_stake = int(position["no"])

        if yes_stake + no_stake <= 0:
            raise gl.vm.UserError("[EXPECTED] NO_POSITION")

        yes_pool = int(market["yes_pool"])
        no_pool = int(market["no_pool"])
        total_pool = yes_pool + no_pool

        status = market["status"]

        if status == "void":
            payout = yes_stake + no_stake

        elif status == "resolved":
            if market["outcome"] == "YES":
                winning_stake = yes_stake
                winning_pool = yes_pool
            else:
                winning_stake = no_stake
                winning_pool = no_pool

            if winning_pool <= 0:
                # Nobody took the winning side. Refund rather than strand.
                payout = yes_stake + no_stake
            else:
                payout = winning_stake * total_pool // winning_pool

        else:
            raise gl.vm.UserError("[EXPECTED] NOT_SETTLED")

        # Effects before interaction: mark the claim, then transfer. If the
        # external message fails the whole call reverts and the claim is
        # still available instead of being burned.
        self.claimed[claim_key] = True
        self._pay(user, payout)

        return json.dumps(
            {"market_id": str(market_id), "user": user, "payout": str(payout)},
            sort_keys=True,
            separators=(",", ":"),
        )

    # =================================================================
    # VIEWS
    # =================================================================

    @gl.public.view
    def get_market(self, market_id: str) -> str:
        return json.dumps(
            self._read_market(market_id), sort_keys=True, separators=(",", ":")
        )

    @gl.public.view
    def get_position(self, market_id: str, user: str) -> str:
        return json.dumps(
            self._read_position(market_id, user),
            sort_keys=True,
            separators=(",", ":"),
        )

    @gl.public.view
    def get_odds(self, market_id: str) -> str:
        market = self._read_market(market_id)

        yes_pool = int(market["yes_pool"])
        no_pool = int(market["no_pool"])
        total = yes_pool + no_pool

        # Basis points, integer only. No float ever reaches the caller.
        if total <= 0:
            yes_bps = 5000
            no_bps = 5000
        else:
            yes_bps = yes_pool * 10000 // total
            no_bps = 10000 - yes_bps

        return json.dumps(
            {
                "yes_bps": str(yes_bps),
                "no_bps": str(no_bps),
                "yes_pool": str(yes_pool),
                "no_pool": str(no_pool),
                "total_pool": str(total),
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    @gl.public.view
    def has_claimed(self, market_id: str, user: str) -> str:
        key = self._claim_key(market_id, user)
        return "true" if key in self.claimed else "false"

    @gl.public.view
    def list_markets(self) -> str:
        ids = [str(x) for x in self.market_ids]
        return json.dumps(ids, separators=(",", ":"))

    @gl.public.view
    def get_counter(self) -> str:
        return str(int(self.counter))

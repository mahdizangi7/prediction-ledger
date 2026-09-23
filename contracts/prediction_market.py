# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *

import json
import datetime


# ============================================================
# CONFIG
# ============================================================

ALLOWED_ASSETS = (
    "BTC",
    "ETH",
    "SOL",
)

COIN_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
}

DISPLAY_NAMES = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "SOL": "Solana",
}

# Historical window around the exact market deadline.
EVIDENCE_WINDOW_SECONDS = 24 * 60 * 60

# The selected historical observation must still be
# reasonably close to the exact deadline.
MAX_OBSERVATION_DISTANCE_SECONDS = 3600

# Independent validator price tolerance.
PRICE_TOLERANCE_RATIO = 0.002
PRICE_TOLERANCE_MIN_USD = 0.50

BAND_RATIO = 0.005
BAND_MIN_USD = 1.0

VOID_GRACE_SECONDS = 7 * 24 * 60 * 60


# ============================================================
# EVM PAYEE INTERFACE
# ============================================================

@gl.evm.contract_interface
class _Payee:
    class View:
        pass

    class Write:
        pass


# ============================================================
# PREDICTION MARKET
# ============================================================

class PredictionMarket(gl.Contract):

    # --------------------------------------------------------
    # Persistent storage
    # --------------------------------------------------------

    counter: u256

    markets: TreeMap[str, str]

    positions: TreeMap[str, str]

    claims: TreeMap[str, str]

    market_ids: DynArray[str]


    # ========================================================
    # CONSTRUCTOR
    # ========================================================

    def __init__(self):
        self.counter = u256(0)


    # ========================================================
    # BASIC HELPERS
    # ========================================================

    def _market_key(
        self,
        market_id: str,
    ) -> str:

        return "market:" + str(market_id)


    def _position_key(
        self,
        market_id: str,
        user: str,
    ) -> str:

        return (
            "position:"
            + str(market_id)
            + ":"
            + str(user).strip().lower()
        )


    def _claim_key(
        self,
        market_id: str,
        user: str,
    ) -> str:

        return (
            "claim:"
            + str(market_id)
            + ":"
            + str(user).strip().lower()
        )


    def _sender(self) -> str:

        return gl.message.sender_address.as_hex.lower()


    def _now(self) -> int:

        raw = gl.message_raw["datetime"]

        try:

            normalized = str(raw).replace(
                "Z",
                "+00:00",
            )

            return int(
                datetime.datetime.fromisoformat(
                    normalized
                ).timestamp()
            )

        except Exception:

            raise gl.vm.UserError(
                "[EXPECTED] INVALID_TRANSACTION_TIMESTAMP"
            )


    def _load_market(
        self,
        market_id: str,
    ):

        key = self._market_key(
            market_id
        )

        if key not in self.markets:

            raise gl.vm.UserError(
                "[EXPECTED] MARKET_NOT_FOUND"
            )

        try:

            return json.loads(
                self.markets[key]
            )

        except Exception:

            raise gl.vm.UserError(
                "[EXPECTED] INVALID_MARKET_STATE"
            )


    def _save_market(
        self,
        market,
    ) -> None:

        key = self._market_key(
            market["id"]
        )

        self.markets[key] = json.dumps(
            market,
            sort_keys=True,
            separators=(",", ":"),
        )


    def _load_position(
        self,
        market_id: str,
        user: str,
    ):

        key = self._position_key(
            market_id,
            user,
        )

        if key not in self.positions:

            return {
                "market_id": str(
                    market_id
                ),
                "user": str(
                    user
                ).lower(),
                "yes": "0",
                "no": "0",
                "total": "0",
            }

        try:

            return json.loads(
                self.positions[key]
            )

        except Exception:

            raise gl.vm.UserError(
                "[EXPECTED] INVALID_POSITION_STATE"
            )


    def _save_position(
        self,
        position,
    ) -> None:

        key = self._position_key(
            position["market_id"],
            position["user"],
        )

        self.positions[key] = json.dumps(
            position,
            sort_keys=True,
            separators=(",", ":"),
        )


    # ========================================================
    # SAFE PUBLIC OUTPUTS
    # ========================================================

    def _safe_market_output(
        self,
        market,
    ):

        return {

            "id": str(
                market.get(
                    "id",
                    "",
                )
            ),

            "question": str(
                market.get(
                    "question",
                    "",
                )
            ),

            "asset": str(
                market.get(
                    "asset",
                    "",
                )
            ),

            "coin_id": str(
                market.get(
                    "coin_id",
                    "",
                )
            ),

            "threshold": str(
                market.get(
                    "threshold",
                    "0",
                )
            ),

            "deadline": str(
                market.get(
                    "deadline",
                    "0",
                )
            ),

            "source": str(
                market.get(
                    "source",
                    "",
                )
            ),

            "status": str(
                market.get(
                    "status",
                    "open",
                )
            ),

            "outcome": str(
                market.get(
                    "outcome",
                    "",
                )
            ),

            "verified": bool(
                market.get(
                    "verified",
                    False,
                )
            ),

            "yes_pool": str(
                market.get(
                    "yes_pool",
                    "0",
                )
            ),

            "no_pool": str(
                market.get(
                    "no_pool",
                    "0",
                )
            ),

            "total_pool": str(
                market.get(
                    "total_pool",
                    "0",
                )
            ),

            "created_at": str(
                market.get(
                    "created_at",
                    "0",
                )
            ),

            "resolved_at": str(
                market.get(
                    "resolved_at",
                    "",
                )
            ),

            "resolution_evidence": market.get(
                "resolution_evidence",
                {},
            ),
        }


    def _safe_position_output(
        self,
        position,
    ):

        return {

            "market_id": str(
                position.get(
                    "market_id",
                    "",
                )
            ),

            "user": str(
                position.get(
                    "user",
                    "",
                )
            ),

            "yes": str(
                position.get(
                    "yes",
                    "0",
                )
            ),

            "no": str(
                position.get(
                    "no",
                    "0",
                )
            ),

            "total": str(
                position.get(
                    "total",
                    "0",
                )
            ),
        }


    # ========================================================
    # HISTORICAL SOURCE
    # ========================================================

    def _build_source(
        self,
        asset: str,
        deadline: int,
    ) -> str:

        coin_id = COIN_IDS[asset]

        start_time = (
            int(deadline)
            - EVIDENCE_WINDOW_SECONDS
        )

        end_time = (
            int(deadline)
            + EVIDENCE_WINDOW_SECONDS
        )

        return (
            "https://api.coingecko.com/api/v3/"
            "coins/"
            + coin_id
            + "/market_chart/range"
            "?vs_currency=usd"
            "&from="
            + str(start_time)
            + "&to="
            + str(end_time)
        )


    # ========================================================
    # HISTORICAL PRICE EXTRACTION
    # ========================================================

    def _extract_historical_price(
        self,
        response_body: str,
        deadline: int,
    ):

        try:

            data = json.loads(
                response_body
            )

        except Exception:

            raise ValueError(
                "INVALID_JSON"
            )


        prices = data.get(
            "prices",
            [],
        )


        if not isinstance(
            prices,
            list,
        ):

            raise ValueError(
                "INVALID_PRICES"
            )


        if len(prices) == 0:

            raise ValueError(
                "NO_HISTORICAL_PRICES"
            )


        best_price = None

        best_timestamp = None

        best_distance = None


        for item in prices:

            if not isinstance(
                item,
                list,
            ):

                continue


            if len(item) < 2:

                continue


            try:

                timestamp_ms = float(
                    item[0]
                )

                price = float(
                    item[1]
                )

            except Exception:

                continue


            if price <= 0:

                continue


            observed_at = int(
                round(
                    timestamp_ms
                    / 1000.0
                )
            )


            distance = abs(
                observed_at
                - int(deadline)
            )


            if (
                best_distance is None
                or distance < best_distance
            ):

                best_price = price

                best_timestamp = (
                    observed_at
                )

                best_distance = (
                    distance
                )


        if best_price is None:

            raise ValueError(
                "NO_VALID_HISTORICAL_PRICE"
            )


        if (
            best_distance
            > MAX_OBSERVATION_DISTANCE_SECONDS
        ):

            raise ValueError(
                "OBSERVATION_TOO_FAR_FROM_DEADLINE"
            )


        return {

            "price": float(
                best_price
            ),

            "observed_at": int(
                best_timestamp
            ),

            "distance_seconds": int(
                best_distance
            ),
        }


    # ========================================================
    # OUTCOME
    # ========================================================

    def _calculate_outcome(
        self,
        price: float,
        threshold: float,
    ):

        if price > threshold:

            return "YES"

        return "NO"


    # ========================================================
    # CREATE MARKET
    # ========================================================

    @gl.public.write
    def create_market(
        self,
        asset: str,
        threshold: str,
        deadline: str,
    ):

        clean_asset = (
            str(asset)
            .upper()
            .strip()
        )


        if clean_asset not in ALLOWED_ASSETS:

            raise gl.vm.UserError(
                "[EXPECTED] UNSUPPORTED_ASSET"
            )


        try:

            threshold_value = float(
                str(threshold)
            )

        except Exception:

            raise gl.vm.UserError(
                "[EXPECTED] INVALID_THRESHOLD"
            )


        if threshold_value <= 0:

            raise gl.vm.UserError(
                "[EXPECTED] INVALID_THRESHOLD"
            )


        try:

            deadline_value = int(
                str(deadline)
            )

        except Exception:

            raise gl.vm.UserError(
                "[EXPECTED] INVALID_DEADLINE"
            )


        now = self._now()


        if deadline_value <= now:

            raise gl.vm.UserError(
                "[EXPECTED] DEADLINE_MUST_BE_IN_FUTURE"
            )


        coin_id = COIN_IDS[
            clean_asset
        ]

        display_name = DISPLAY_NAMES[
            clean_asset
        ]


        source = self._build_source(
            clean_asset,
            deadline_value,
        )


        self.counter = u256(
            int(self.counter) + 1
        )


        market_id = str(
            int(self.counter)
        )


        question = (
            "Will "
            + display_name
            + " ("
            + clean_asset
            + ") be above $"
            + str(threshold_value)
            + " at the market deadline?"
        )


        market = {

            "id": market_id,

            "question": question,

            "asset": clean_asset,

            "coin_id": coin_id,

            "threshold": str(
                threshold_value
            ),

            "deadline": str(
                deadline_value
            ),

            "source": source,

            "status": "open",

            "outcome": "",

            "verified": False,

            "yes_pool": "0",

            "no_pool": "0",

            "total_pool": "0",

            "created_at": str(
                now
            ),

            "resolved_at": "",

            "resolution_evidence": {},
        }


        self._save_market(
            market
        )


        self.market_ids.append(
            market_id
        )


        return self._safe_market_output(
            market
        )


    # ========================================================
    # PLACE BET
    # ========================================================

    @gl.public.write.payable
    def place_bet(
        self,
        market_id: str,
        side: str,
    ):

        market = self._load_market(
            market_id
        )


        if market["status"] != "open":

            raise gl.vm.UserError(
                "[EXPECTED] MARKET_NOT_OPEN"
            )


        now = self._now()

        deadline = int(
            market["deadline"]
        )


        if now >= deadline:

            raise gl.vm.UserError(
                "[EXPECTED] BETTING_DEADLINE_PASSED"
            )


        clean_side = (
            str(side)
            .upper()
            .strip()
        )


        if clean_side not in (
            "YES",
            "NO",
        ):

            raise gl.vm.UserError(
                "[EXPECTED] INVALID_SIDE"
            )


        amount = int(
            gl.message.value
        )


        if amount <= 0:

            raise gl.vm.UserError(
                "[EXPECTED] BET_VALUE_MUST_BE_POSITIVE"
            )


        user = self._sender()


        position = self._load_position(
            market_id,
            user,
        )


        if clean_side == "YES":

            position["yes"] = str(
                int(position["yes"])
                + amount
            )

            market["yes_pool"] = str(
                int(market["yes_pool"])
                + amount
            )

        else:

            position["no"] = str(
                int(position["no"])
                + amount
            )

            market["no_pool"] = str(
                int(market["no_pool"])
                + amount
            )


        position["total"] = str(
            int(position["yes"])
            + int(position["no"])
        )


        market["total_pool"] = str(
            int(market["yes_pool"])
            + int(market["no_pool"])
        )


        self._save_position(
            position
        )


        self._save_market(
            market
        )


        return {

            "market_id": str(
                market_id
            ),

            "user": user,

            "side": clean_side,

            "amount": str(
                amount
            ),

            "position": self._safe_position_output(
                position
            ),

            "market": self._safe_market_output(
                market
            ),
        }


    # ========================================================
    # RESOLVE MARKET
    # ========================================================

    @gl.public.write
    def resolve_market(
        self,
        market_id: str,
    ):

        market = self._load_market(
            market_id
        )


        if market["status"] != "open":

            raise gl.vm.UserError(
                "[EXPECTED] MARKET_NOT_OPEN"
            )


        deadline = int(
            market["deadline"]
        )


        now = self._now()


        if now < deadline:

            raise gl.vm.UserError(
                "[EXPECTED] DEADLINE_NOT_REACHED"
            )


        stored_asset = str(
            market["asset"]
        ).upper()


        stored_coin_id = str(
            market["coin_id"]
        )


        stored_threshold = float(
            market["threshold"]
        )


        stored_source = str(
            market["source"]
        )


        expected_source = self._build_source(
            stored_asset,
            deadline,
        )


        if stored_asset not in ALLOWED_ASSETS:

            raise gl.vm.UserError(
                "[EXPECTED] INVALID_STORED_ASSET"
            )


        if (
            stored_coin_id
            != COIN_IDS[stored_asset]
        ):

            raise gl.vm.UserError(
                "[EXPECTED] INVALID_STORED_COIN_ID"
            )


        if (
            stored_source
            != expected_source
        ):

            raise gl.vm.UserError(
                "[EXPECTED] INVALID_STORED_SOURCE"
            )


        # ====================================================
        # LEADER
        # ====================================================

        def leader_fn():

            response = gl.nondet.web.get(
                stored_source
            )


            body = response.body.decode(
                "utf-8"
            )


            observation = (
                self._extract_historical_price(
                    body,
                    deadline,
                )
            )


            price = float(
                observation["price"]
            )


            observed_at = int(
                observation["observed_at"]
            )


            distance_seconds = int(
                observation[
                    "distance_seconds"
                ]
            )


            outcome = (
                self._calculate_outcome(
                    price,
                    stored_threshold,
                )
            )


            # IMPORTANT:
            # run_nondet_unsafe / gl.vm.Return must
            # receive calldata-encodable values.
            # Floats are converted to strings here.
            return {

                "asset": str(
                    stored_asset
                ),

                "coin_id": str(
                    stored_coin_id
                ),

                "deadline": str(
                    deadline
                ),

                "source": str(
                    stored_source
                ),

                "observed_at": str(
                    observed_at
                ),

                "price": str(
                    price
                ),

                "distance_seconds": str(
                    distance_seconds
                ),

                "outcome": str(
                    outcome
                ),
            }


        # ====================================================
        # VALIDATOR
        # ====================================================

        def validator_fn(
            leader_result,
        ) -> bool:

            if not isinstance(
                leader_result,
                gl.vm.Return,
            ):

                return False


            leader = (
                leader_result.calldata
            )


            try:

                # --------------------------------------------
                # Static fields
                # --------------------------------------------

                if (
                    str(
                        leader["asset"]
                    ).upper()
                    != stored_asset
                ):

                    return False


                if (
                    str(
                        leader["coin_id"]
                    )
                    != stored_coin_id
                ):

                    return False


                if (
                    int(
                        leader["deadline"]
                    )
                    != deadline
                ):

                    return False


                if (
                    str(
                        leader["source"]
                    )
                    != stored_source
                ):

                    return False


                leader_price = float(
                    leader["price"]
                )


                leader_observed_at = int(
                    leader["observed_at"]
                )


                leader_distance = int(
                    leader["distance_seconds"]
                )


                leader_outcome = str(
                    leader["outcome"]
                ).upper()


                if leader_price <= 0:

                    return False


                if leader_outcome not in (
                    "YES",
                    "NO",
                ):

                    return False


                if leader_distance < 0:

                    return False


                if (
                    leader_distance
                    > MAX_OBSERVATION_DISTANCE_SECONDS
                ):

                    return False


                # --------------------------------------------
                # Independent validator fetch
                # --------------------------------------------

                response = gl.nondet.web.get(
                    stored_source
                )


                body = response.body.decode(
                    "utf-8"
                )


                validator_observation = (
                    self._extract_historical_price(
                        body,
                        deadline,
                    )
                )


                validator_price = float(
                    validator_observation[
                        "price"
                    ]
                )


                validator_observed_at = int(
                    validator_observation[
                        "observed_at"
                    ]
                )


                validator_distance = int(
                    validator_observation[
                        "distance_seconds"
                    ]
                )


                if validator_price <= 0:

                    return False


                if (
                    validator_distance
                    > MAX_OBSERVATION_DISTANCE_SECONDS
                ):

                    return False


                # --------------------------------------------
                # Observation timestamp agreement
                # --------------------------------------------

                if (
                    leader_observed_at
                    != validator_observed_at
                ):

                    return False


                # --------------------------------------------
                # Distance agreement
                # --------------------------------------------

                if (
                    leader_distance
                    != validator_distance
                ):

                    return False


                # --------------------------------------------
                # Both observations must be tied to
                # the stored deadline.
                # --------------------------------------------

                if (
                    abs(
                        leader_observed_at
                        - deadline
                    )
                    > MAX_OBSERVATION_DISTANCE_SECONDS
                ):

                    return False


                if (
                    abs(
                        validator_observed_at
                        - deadline
                    )
                    > MAX_OBSERVATION_DISTANCE_SECONDS
                ):

                    return False


                # --------------------------------------------
                # Price tolerance
                # --------------------------------------------

                price_difference = abs(
                    leader_price
                    - validator_price
                )


                allowed_difference = max(
                    PRICE_TOLERANCE_MIN_USD,
                    abs(leader_price)
                    * PRICE_TOLERANCE_RATIO,
                )


                if (
                    price_difference
                    > allowed_difference
                ):

                    return False


                # --------------------------------------------
                # Validator independently derives outcome.
                # --------------------------------------------

                validator_outcome = (
                    self._calculate_outcome(
                        validator_price,
                        stored_threshold,
                    )
                )


                if (
                    validator_outcome
                    != leader_outcome
                ):

                    return False


                # --------------------------------------------
                # Leader outcome must match leader price.
                # --------------------------------------------

                leader_derived_outcome = (
                    self._calculate_outcome(
                        leader_price,
                        stored_threshold,
                    )
                )


                if (
                    leader_derived_outcome
                    != leader_outcome
                ):

                    return False


                return True


            except Exception:

                return False


        # ====================================================
        # CONSENSUS
        # ====================================================

        result = gl.vm.run_nondet_unsafe(
            leader_fn,
            validator_fn,
        )


        # ====================================================
        # PERSIST VERIFIED EVIDENCE
        # ====================================================

        try:

            final_asset = str(
                result["asset"]
            ).upper()


            final_coin_id = str(
                result["coin_id"]
            )


            final_deadline = int(
                result["deadline"]
            )


            final_source = str(
                result["source"]
            )


            final_observed_at = int(
                result["observed_at"]
            )


            final_price = float(
                result["price"]
            )


            final_distance = int(
                result["distance_seconds"]
            )


            final_outcome = str(
                result["outcome"]
            ).upper()


        except Exception:

            raise gl.vm.UserError(
                "[EXPECTED] INVALID_CONSENSUS_RESULT"
            )


        if final_asset != stored_asset:

            raise gl.vm.UserError(
                "[EXPECTED] CONSENSUS_ASSET_MISMATCH"
            )


        if final_coin_id != stored_coin_id:

            raise gl.vm.UserError(
                "[EXPECTED] CONSENSUS_COIN_ID_MISMATCH"
            )


        if final_deadline != deadline:

            raise gl.vm.UserError(
                "[EXPECTED] CONSENSUS_DEADLINE_MISMATCH"
            )


        if final_source != stored_source:

            raise gl.vm.UserError(
                "[EXPECTED] CONSENSUS_SOURCE_MISMATCH"
            )


        if final_observed_at <= 0:

            raise gl.vm.UserError(
                "[EXPECTED] CONSENSUS_OBSERVATION_INVALID"
            )


        if (
            abs(
                final_observed_at
                - deadline
            )
            > MAX_OBSERVATION_DISTANCE_SECONDS
        ):

            raise gl.vm.UserError(
                "[EXPECTED] CONSENSUS_OBSERVATION_TOO_FAR"
            )


        if final_distance < 0:

            raise gl.vm.UserError(
                "[EXPECTED] CONSENSUS_DISTANCE_INVALID"
            )


        if (
            final_distance
            > MAX_OBSERVATION_DISTANCE_SECONDS
        ):

            raise gl.vm.UserError(
                "[EXPECTED] CONSENSUS_DISTANCE_TOO_FAR"
            )


        if final_price <= 0:

            raise gl.vm.UserError(
                "[EXPECTED] CONSENSUS_PRICE_INVALID"
            )


        if final_outcome not in (
            "YES",
            "NO",
        ):

            raise gl.vm.UserError(
                "[EXPECTED] CONSENSUS_OUTCOME_INVALID"
            )


        deterministic_outcome = (
            self._calculate_outcome(
                final_price,
                stored_threshold,
            )
        )


        if (
            deterministic_outcome
            != final_outcome
        ):

            raise gl.vm.UserError(
                "[EXPECTED] CONSENSUS_OUTCOME_PRICE_MISMATCH"
            )


        # ====================================================
        # RESOLVE
        # ====================================================

        market["status"] = "resolved"

        market["outcome"] = (
            final_outcome
        )

        market["verified"] = True

        market["resolved_at"] = str(
            now
        )


        market[
            "resolution_evidence"
        ] = {

            "asset": final_asset,

            "coin_id": final_coin_id,

            "deadline": str(
                final_deadline
            ),

            "source": final_source,

            "observed_at": str(
                final_observed_at
            ),

            "price": str(
                final_price
            ),

            "distance_seconds": str(
                final_distance
            ),

            "outcome": final_outcome,

            "price_tolerance_ratio": str(
                PRICE_TOLERANCE_RATIO
            ),

            "price_tolerance_min_usd": str(
                PRICE_TOLERANCE_MIN_USD
            ),

            "verified": True,
        }


        self._save_market(
            market
        )


        return {

            "market_id": str(
                market_id
            ),

            "status": "resolved",

            "outcome": final_outcome,

            "verified": True,

            "resolved_at": str(
                now
            ),

            "evidence": {

                "asset": final_asset,

                "coin_id": final_coin_id,

                "deadline": str(
                    final_deadline
                ),

                "source": final_source,

                "observed_at": str(
                    final_observed_at
                ),

                "price": str(
                    final_price
                ),

                "distance_seconds": str(
                    final_distance
                ),

                "outcome": final_outcome,
            },
        }


    # ========================================================
    # CLAIM
    # ========================================================

    @gl.public.write
    def claim(
        self,
        market_id: str,
    ):

        market = self._load_market(
            market_id
        )


        if market["status"] != "resolved":

            raise gl.vm.UserError(
                "[EXPECTED] MARKET_NOT_RESOLVED"
            )


        if not market.get(
            "verified",
            False,
        ):

            raise gl.vm.UserError(
                "[EXPECTED] MARKET_NOT_VERIFIED"
            )


        user = self._sender()


        claim_key = self._claim_key(
            market_id,
            user,
        )


        if claim_key in self.claims:

            raise gl.vm.UserError(
                "[EXPECTED] ALREADY_CLAIMED"
            )


        position = self._load_position(
            market_id,
            user,
        )


        if (
            int(position["total"])
            <= 0
        ):

            raise gl.vm.UserError(
                "[EXPECTED] NO_POSITION"
            )


        outcome = str(
            market["outcome"]
        ).upper()


        if outcome == "YES":

            winning_position = int(
                position["yes"]
            )

            winning_pool = int(
                market["yes_pool"]
            )

        elif outcome == "NO":

            winning_position = int(
                position["no"]
            )

            winning_pool = int(
                market["no_pool"]
            )

        else:

            raise gl.vm.UserError(
                "[EXPECTED] INVALID_OUTCOME"
            )


        if winning_position <= 0:

            raise gl.vm.UserError(
                "[EXPECTED] LOSING_POSITION"
            )


        if winning_pool <= 0:

            raise gl.vm.UserError(
                "[EXPECTED] EMPTY_WINNING_POOL"
            )


        total_pool = int(
            market["total_pool"]
        )


        payout = (
            winning_position
            * total_pool
            // winning_pool
        )


        if payout <= 0:

            raise gl.vm.UserError(
                "[EXPECTED] ZERO_PAYOUT"
            )


        try:

            contract_balance = int(
                self.balance
            )

        except Exception:

            contract_balance = 0


        if (
            contract_balance > 0
            and payout > contract_balance
        ):

            raise gl.vm.UserError(
                "[EXPECTED] INSUFFICIENT_CONTRACT_BALANCE"
            )


        self.claims[
            claim_key
        ] = "true"


        _Payee(
            Address(user)
        ).emit_transfer(
            value=u256(
                payout
            )
        )


        return {

            "market_id": str(
                market_id
            ),

            "user": user,

            "outcome": outcome,

            "winning_position": str(
                winning_position
            ),

            "winning_pool": str(
                winning_pool
            ),

            "total_pool": str(
                total_pool
            ),

            "payout": str(
                payout
            ),

            "claimed": True,
        }


    # ========================================================
    # GET MARKET
    # ========================================================

    @gl.public.view
    def get_market(
        self,
        market_id: str,
    ):

        market = self._load_market(
            market_id
        )

        return self._safe_market_output(
            market
        )


    # ========================================================
    # GET POSITION
    # ========================================================

    @gl.public.view
    def get_position(
        self,
        market_id: str,
        user: str,
    ):

        position = self._load_position(
            market_id,
            user,
        )

        return self._safe_position_output(
            position
        )


    # ========================================================
    # HAS CLAIMED
    # ========================================================

    @gl.public.view
    def has_claimed(
        self,
        market_id: str,
        user: str,
    ) -> bool:

        key = self._claim_key(
            market_id,
            user,
        )

        return key in self.claims


    # ========================================================
    # COUNTER
    # ========================================================

    @gl.public.view
    def get_counter(
        self,
    ) -> str:

        return str(
            int(self.counter)
        )


    # ========================================================
    # LATEST ID
    # ========================================================

    @gl.public.view
    def get_latest_id(
        self,
    ) -> str:

        if int(self.counter) <= 0:

            return "0"

        return str(
            int(self.counter)
        )


    # ========================================================
    # LIST MARKETS
    # ========================================================

    @gl.public.view
    def list_markets(
        self,
    ):

        result = []


        for market_id in self.market_ids:

            try:

                market = self._load_market(
                    market_id
                )

                result.append(
                    self._safe_market_output(
                        market
                    )
                )

            except Exception:

                continue


        return result


    # ========================================================
    # ODDS
    # ========================================================

    @gl.public.view
    def get_odds(
        self,
        market_id: str,
    ):

        market = self._load_market(
            market_id
        )


        yes_pool = float(
            market["yes_pool"]
        )

        no_pool = float(
            market["no_pool"]
        )

        total_pool = float(
            market["total_pool"]
        )


        if total_pool <= 0:

            yes_probability = 0.0

            no_probability = 0.0

        else:

            yes_probability = (
                yes_pool
                / total_pool
                * 100.0
            )

            no_probability = (
                no_pool
                / total_pool
                * 100.0
            )


        return {

            "market_id": str(
                market_id
            ),

            "yes_pool": str(
                market["yes_pool"]
            ),

            "no_pool": str(
                market["no_pool"]
            ),

            "total_pool": str(
                market["total_pool"]
            ),

            "yes_probability": str(
                yes_probability
            ),

            "no_probability": str(
                no_probability
            ),
        }


    # ========================================================
    # RESOLUTION EVIDENCE
    # ========================================================

    @gl.public.view
    def get_resolution_evidence(
        self,
        market_id: str,
    ):

        market = self._load_market(
            market_id
        )


        evidence = market.get(
            "resolution_evidence",
            {},
        )


        if not evidence:

            return {

                "market_id": str(
                    market_id
                ),

                "verified": False,

                "evidence": {},
            }


        return {

            "market_id": str(
                market_id
            ),

            "verified": bool(
                market.get(
                    "verified",
                    False,
                )
            ),

            "evidence": {

                "asset": str(
                    evidence.get(
                        "asset",
                        "",
                    )
                ),

                "coin_id": str(
                    evidence.get(
                        "coin_id",
                        "",
                    )
                ),

                "deadline": str(
                    evidence.get(
                        "deadline",
                        "0",
                    )
                ),

                "source": str(
                    evidence.get(
                        "source",
                        "",
                    )
                ),

                "observed_at": str(
                    evidence.get(
                        "observed_at",
                        "0",
                    )
                ),

                "price": str(
                    evidence.get(
                        "price",
                        "0",
                    )
                ),

                "distance_seconds": str(
                    evidence.get(
                        "distance_seconds",
                        "0",
                    )
                ),

                "outcome": str(
                    evidence.get(
                        "outcome",
                        "",
                    )
                ),

                "price_tolerance_ratio": str(
                    evidence.get(
                        "price_tolerance_ratio",
                        PRICE_TOLERANCE_RATIO,
                    )
                ),

                "price_tolerance_min_usd": str(
                    evidence.get(
                        "price_tolerance_min_usd",
                        PRICE_TOLERANCE_MIN_USD,
                    )
                ),

                "verified": bool(
                    evidence.get(
                        "verified",
                        False,
                    )
                ),
            },
        }

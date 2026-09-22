# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

# Deploy this FIRST, call probe(), and read get_result().
# Whichever line reports "ok" with a sane epoch value is the one to use
# in PredictionMarket._now(). Do not trust the docs here - trust this.

from genlayer import *

import json


class TimeProbe(gl.Contract):
    result: str

    def __init__(self):
        self.result = ""

    @gl.public.write
    def probe(self) -> None:
        out = {}

        # candidate 1: patched datetime module
        try:
            import datetime

            out["datetime_now"] = str(
                int(datetime.datetime.now(datetime.timezone.utc).timestamp())
            )
        except Exception as e:
            out["datetime_now"] = "ERR: " + str(e)

        # candidate 2: raw message datetime (SDK dev branch)
        try:
            out["message_raw"] = str(gl.message.raw["datetime"])
        except Exception as e:
            out["message_raw"] = "ERR: " + str(e)

        # candidate 3: internal message dict (used by some testnet contracts)
        try:
            import genlayer._internal.msg as _msg

            out["internal_msg"] = str(_msg.message_raw["datetime"])
        except Exception as e:
            out["internal_msg"] = "ERR: " + str(e)

        # candidate 4: time module (expected to be absent or non-deterministic)
        try:
            import time

            out["time_time"] = str(int(time.time()))
        except Exception as e:
            out["time_time"] = "ERR: " + str(e)

        self.result = json.dumps(out, sort_keys=True, separators=(",", ":"))

    @gl.public.view
    def get_result(self) -> str:
        return self.result

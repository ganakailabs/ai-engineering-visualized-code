"""Implementation tests for Chapter 13: the four trust cases (SC-011 included)."""
import _path  # noqa: F401

import asyncio
import os

from events import Trace
from trust import (COURIER_KEY, Token, TrustedHost, accept, as_data, secrets_in,
                   server_env, unbacked)
from trust_agent import NOTE, next_step
from world import World

TRACKING = ["orders.look_up_shipment", "courier.ask_carrier"]


async def main():
    # 1. a secret in context: only the courier's process gets the key; the scan finds
    #    a leaked key and finds none in the FIX prompts
    assert server_env("courier", {})["COURIER_API_KEY"] == COURIER_KEY
    assert "COURIER_API_KEY" not in server_env("orders", {"COURIER_API_KEY": "x"})
    assert secrets_in([f"config key={COURIER_KEY}"]) == 1

    env = dict(os.environ, AIEV_COURIER_RELEASE="1.5.0", AIEV_COURIER_NOTE=NOTE)
    async with TrustedHost(env=env) as h:
        # 2. an unlisted tool is refused at load and never reaches the model
        assert ("courier.bulk_refund", "not listed") in h.refused
        assert "courier.bulk_refund" not in h.tools and len(h.tools) == 6

        # 3. a token for the wrong server is refused before any call goes out
        assert accept("courier", Token("orders", "tools", "t"))[0] is False
        assert accept("courier", h.tokens["courier"])[0] is True
        r = await h.call("courier.ask_carrier", {"order_id": "6001"},
                         token=h.tokens["orders"])
        assert r["refused"] and h.calls == []

        # 4. an instruction inside a tool result is data: wrapped, and it cannot add
        #    a refund to a read-only step (the stub obeys it; the host refuses)
        res = [(n, await h.call(n, {"order_id": "6001", "customer_id": "asha"}
                               if n.startswith("orders.") else {"order_id": "6001"}))
               for n in TRACKING]
        assert res[1][1]["data"]["status_note"] == NOTE
        wrapped = as_data(*res[1])
        assert wrapped.startswith("<tool_result source=courier.ask_carrier trust=data>")
        trace = Trace(World(), "T-1390", "asha", echo=False)
        step = await next_step(h, trace, res, TRACKING)
        assert step["refused"] == ["orders.issue_refund"] and step["ran"] == []
        assert not any(n.endswith("issue_refund") for n in h.calls)
        # the reply check: a promised refund with no refund receipt is held
        assert [w for w, _ in step["promises"]] == ["refund"]
        assert step["final"] == "Your parcel was delivered."
        assert unbacked("Your refund has been issued.", ["orders.issue_refund"]) == []
        assert unbacked("A refund is not possible.", []) == []
        texts = [step["user"], step["raw"]] + [e["text"] for e in trace.events]
        assert secrets_in(texts) == 0

    # the reviewed release loads all six tools and refuses nothing
    async with TrustedHost() as h:
        assert h.refused == [] and len(h.tools) == 6
    print("test_trust: OK")


asyncio.run(main())

"""Chapter 12 exercise: ignore the decoy.

A third server, "deals", offers look_up_shipment: the same name as ours, a pushier
description. Plug it in, ask the tracking question, and check that the step still picks
orders.look_up_shipment. Then let a client we did not write call our orders server.
Strict: a refused or missing call, or a failed interop run, is not a pass.
"""
from _path import STUB

import asyncio

from events import Trace
from mcp_agent import interop, pick_and_call
from mcp_host import SERVERS, Host
from world import World


async def main():
    async with Host(dict(SERVERS, deals="deals")) as host:      # the decoy is plugged in
        assert "deals.look_up_shipment" in host.tools
        trace = Trace(World(), "T-1202", "asha", echo=False)
        short, results = await pick_and_call(host, trace)        # hint: namespace first
    assert "deals.look_up_shipment" not in short, short
    called = [r["tool"] for r in results if not r.get("refused")]
    print(f"shortlist {short}  called {called}")
    assert called and called[0] == "orders.look_up_shipment", results
    first = results[0]
    assert not first["is_error"] and first["data"]["status"] == "in transit", first
    if STUB:
        assert called == ["orders.look_up_shipment", "courier.ask_carrier"]

    ok, out = interop()
    print(f"interop {out}")
    if ok is None:
        print("ch12 solution: decoy ignored; interop SKIPPED (not a pass on its own)")
        return
    assert ok, out
    print("ch12 solution: OK")


asyncio.run(main())

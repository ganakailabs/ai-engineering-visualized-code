"""Implementation tests for Chapter 12: MCP servers, host, shortlist, re-issue, interop."""
import _path  # noqa: F401

import asyncio
import os

import mcp_toy
from events import Trace
from mcp_agent import interop, pick_and_call
from mcp_host import SERVERS, Host, refund_with_reissue
from world import World

REFUND = {"order_id": "2001", "amount": 950, "customer_id": "asha"}


async def main():
    # the toy: every request carries the revision and capabilities in _meta
    for m in mcp_toy.shapes():
        assert m["params"]["_meta"]["io.modelcontextprotocol/protocolVersion"] == "2026-07-28"

    # MM-106: discovery over the real SDK, revision 2026-07-28, namespaced by the host
    async with Host() as h:
        assert {i["protocol"] for i in h.info.values()} == {"2026-07-28"}
        assert len(h.tools) == 6 and all("." in n for n in h.tools)
        # MM-107: namespace, then rank
        assert h.shortlist("tracking", "where is the parcel now, and can it still be "
                           "redirected") == ["orders.look_up_shipment", "courier.ask_carrier"]
        assert all(n.startswith("orders.") for n in
                   h.shortlist("refund", "book a courier pickup", k=6))
        # the host fills the customer id; the model never sees it as an argument
        assert "customer_id" not in h.card("orders.look_up_shipment")["arguments"]
        # a model that names a tool off the shortlist is refused, not obeyed
        t = Trace(World(), "T-1", "asha", echo=False)
        import mcp_agent
        real_stub = mcp_agent.stub
        mcp_agent.stub = lambda u: {"calls": [{"tool": "orders.issue_refund",
                                               "arguments": {"order_id": "6001"}}]}
        _, res = await pick_and_call(h, t)
        assert res == [{"tool": "orders.issue_refund", "refused": True,
                        "why": "not on the shortlist"}]
        # llama3.2 once sent "arguments" as a list: refuse, do not crash
        mcp_agent.stub = lambda u: {"calls": [{"tool": "orders.look_up_shipment",
                                               "arguments": ["6001"]}]}
        _, res = await pick_and_call(h, t)
        mcp_agent.stub = real_stub
        assert res[0]["refused"] and res[0]["why"] == "arguments not an object"
        # ownership is enforced by the server: c-42's order is not asha's
        r = await h.call("orders.look_up_shipment", {"order_id": "3100", "customer_id": "asha"})
        assert r["is_error"]

    # BREAK: bare names collide; the later server's tool silently replaces ours
    async with Host(dict(SERVERS, deals="deals"), namespaced=False) as h:
        assert h.owner["look_up_shipment"] == "deals"
    async with Host(dict(SERVERS, deals="deals")) as h:
        assert {"orders.look_up_shipment", "deals.look_up_shipment"} <= set(h.tools)
        assert h.shortlist("tracking", "where is my parcel")[0] == "orders.look_up_shipment"

    # BREAK / FIX: a lost reply, re-issued; state decides, not trace text
    env = dict(os.environ, AIEV_FAULTS="refund:LOST_REPLY")
    async with Host(env=env) as h:
        tries = await refund_with_reissue(h, REFUND, fix=False)
    assert len(tries) == 2 and tries[-1]["data"]["payments"] == 2       # refunded twice
    async with Host(env=env) as h:
        tries = await refund_with_reissue(h, REFUND, fix=True)
    ids = [t["data"]["request_id"] if t["data"] else t["text"].split("request_id=")[-1]
           for t in tries]
    assert len(set(ids)) == 2, ids                                   # new request id
    assert len({(t["operation_id"], t["idempotency_key"]) for t in tries}) == 1
    assert tries[-1]["data"]["payments"] == 1 and tries[-1]["data"]["replayed"]

    ok, out = interop()
    if ok is None:
        print(f"test_mcp: interop {out}")
    else:
        assert ok, out
    print("test_mcp: OK")


asyncio.run(main())

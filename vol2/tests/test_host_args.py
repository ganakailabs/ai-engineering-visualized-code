"""Ch12 audit: a decoy name and list-valued arguments get explicit errors from the
host, not crashes, and no request is sent."""
import _path  # noqa: F401

import asyncio
from types import SimpleNamespace

import mcp_host

host = mcp_host.Host(servers={})
host.tools["orders.look_up_order"] = SimpleNamespace(
    name="look_up_order", description="Look up one order.",
    input_schema={"properties": {"order_id": {"type": "string"}}})
host.owner["orders.look_up_order"] = "orders"
host.clients["orders"] = None            # any real request would crash on None

for name, args, want in (("orders.issue_refund_now", {}, "unknown tool"),
                         ("orders.look_up_order", {"order_id": ["2001", "2077"]},
                          "must be string"),
                         ("orders.look_up_order", {"amount": 9}, "unknown argument")):
    r = asyncio.run(host.call(name, args))
    assert r["is_error"] and want in r["text"], r
print("ok host refuses decoy names and wrong argument types")

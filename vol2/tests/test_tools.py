"""Contract tests for Chapter 2 tools, against the mock world."""
import _path  # noqa: F401

import ch02
import tools
from harness import Session
from world import World

ASHA, C42, R = Session("asha"), Session("c-42"), tools.ISSUE_REFUND

assert tools.canon("order_id", " #2001") == "2001"
assert [tools.canon("inr", v) for v in (950, "INR 950", "Rs. 950", "950.00")] == [950] * 4
for bad in ("9.5", "-950", "nine"):
    try:
        tools.canon("inr", bad)
        raise AssertionError(bad)
    except tools.BadArg:
        pass

w = World()
r = tools.call(R, w, C42, {"order_id": "3100", "amount_inr": "12500"}, key="k")
assert (r["error"], r["class"], r["next_step"]) == ("AMOUNT_OVER_CAP", "business",
                                                    "request_approval")
assert tools.call(R, w, ASHA, {"order_id": "3100", "amount_inr": 100},
                  key="k")["error"] == "NOT_YOUR_ORDER"
assert tools.call(R, w, ASHA, {"order_id": "2001", "amount_inr": 9500},
                  key="k")["error"] == "AMOUNT_NOT_ORDER_TOTAL"
# a split that slips under the cap (seen from llama3.2, Oct 22, 2026) is refused
assert tools.call(R, w, C42, {"order_id": "3100", "amount_inr": 5000},
                  key="k")["error"] == "AMOUNT_NOT_ORDER_TOTAL"
assert tools.ISSUE_REFUND.exposure(w, {"order_id": "3100", "amount_inr": 5000}) == 12500
assert tools.call(R, w, ASHA, {"order_id": "2001", "amount_inr": 950})["error"] == "MISSING_KEY"
assert tools.call(R, w, ASHA, {"order": "2001"}, key="k")["error"] == "BAD_ARGS"
assert w.payments == []

# a preview is not a reservation: the world changes before the real call
w = World()
p = tools.call(R, w, ASHA, {"order_id": "2001", "amount_inr": 950}, dry_run=True)
assert p["preview"] == "INR 950 on #2001" and p["reserved"] is False and w.payments == []
w.refund("2001", 950, key="k-teammate")                 # a teammate refunds it first
r = tools.call(R, w, ASHA, {"order_id": "2001", "amount_inr": 950}, key="k-mine")
assert r["error"] == "ALREADY_REFUNDED" and len(w.payments) == 1

# transient errors are retried with the same key; the payment lands once
w = World(faults={"refund": ["TIMEOUT"]})
first = tools.call(R, w, ASHA, {"order_id": "2001", "amount_inr": 950}, key="k1")
assert first["class"] == "transient" and w.payments == []
assert tools.call(R, w, ASHA, {"order_id": "2001", "amount_inr": 950}, key="k1")["ok"]
assert len(w.payments) == 1

# output validation: a tool reply that does not match its call is rejected
liar = tools.Spec(**{**R.__dict__, "run": lambda world, a, key: {
    "receipt_id": "pay-x", "order_id": a["order_id"], "amount": a["amount_inr"] * 10}})
assert tools.call(liar, World(), ASHA, {"order_id": "2001", "amount_inr": 950},
                  key="k")["error"] == "BAD_TOOL_OUTPUT"

# BREAK/FIX strip "The Unlimited Write": lost reply plus one retry
assert len(ch02.unlimited_write(False).payments) == 2      # BREAK, documented
assert len(ch02.unlimited_write(True).payments) == 1       # FIX
print("test_tools: OK")

"""Implementation tests for Chapter 1: the harness, the contract, the identity chain."""
import _path  # noqa: F401

import ch01
from harness import REGISTRY, Harness, Limits, Session, Tool
from world import World

ASHA = Session("asha")

# 1. a tool the registry does not hold is refused
w = World()
s = ch01.harness(w, ch01.rogue, "scripted").run(ch01.REFUND, "refund", ASHA, echo=False)
assert s["refused"][0]["reason"] == "not in registry" and w.payments == []

# 2. a forged order id is refused, and no money moves
w = World()
s = ch01.harness(w).run(ch01.FORGED, "refund", ASHA, echo=False)
assert s["refused"][0]["reason"] == "not the caller's order" and w.payments_for("3100") == []

# 3. a proposal never reaches a tool without authorization
calls = []
spy = dict(REGISTRY, issue_refund=Tool("issue_refund",
                                       lambda world, session, **a: calls.append(a) or {},
                                       writes=True))
w = World()
Harness(model=ch01.model, tools=spy, world=w).run(ch01.FORGED, "refund", ASHA,
                                                  echo=False)
assert calls == [], "a refused proposal reached the tool"

# 4. the step limit stops a model that never finishes
def looping(context, offered):
    return {"action": "look_up_shipment", "args": {"order_id": "6001"}}


w = World()
s = Harness(model=looping, tools=REGISTRY, world=w, limits=Limits(steps=3)).run(
    ch01.ADDRESS, "address change", ASHA, echo=False)
assert len(s["steps"]) == 3 and s["outcome"] == "escalate: step limit reached"

# 5. the happy path pays once, the order's own amount
w = World()
ch01.harness(w).run(ch01.REFUND, "refund", ASHA, echo=False)
assert [(p["order_id"], p["amount"]) for p in w.payments] == [("2001", 950)]

# 6. BREAK/FIX strip: tracking on the fixed chain makes no model call
w, asked = World(), []
Harness(model=lambda c, o: asked.append(c) or {"final": "x"}, tools=REGISTRY,
        world=w).run("Where is my parcel #6001?", "tracking", ASHA, echo=False)
assert asked == []
print("test_harness: OK")

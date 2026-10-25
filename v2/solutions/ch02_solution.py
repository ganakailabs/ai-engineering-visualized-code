"""Chapter 2 exercise: add a safe cancel_order, test first.

A class (write), a cap (orders above INR 5,000 need approval), a required key, a
precondition checked inside the tool (still packing) and a preview.
"""
from _path import STUB  # noqa: F401

import tools
from harness import Session
from world import World


def cancel_pre(world, args):
    if world.shipment(args["order_id"]) != "packing":
        return "ALREADY_SHIPPED"
    if world.order(args["order_id"])["amount"] > tools.CAP_INR:
        return "AMOUNT_OVER_CAP"
    return None


CANCEL_ORDER = tools.Spec(
    name="cancel_order",
    does="Cancel an order that is still packing, once.",
    args={"order_id": "order_id"},
    errors={"ALREADY_SHIPPED": ("business", "offer a return once it is delivered"),
            "AMOUNT_OVER_CAP": ("business", "request_approval")},
    run=lambda world, a, key: world.cancel_order(a["order_id"], key=key),
    writes=True, precondition=cancel_pre,
    preview=lambda world, a: f"cancel #{a['order_id']} ({world.shipment(a['order_id'])})",
    receipt_fields=("receipt_id", "order_id"),
    checks_out=[lambda a, r: r["order_id"] == a["order_id"]])

ASHA = Session("asha")
KEY = "k-T-5120-a-cancel-5120"

# The contract test. 1. The order ships between the preview and the real call.
world = World()
preview = tools.call(CANCEL_ORDER, world, ASHA, {"order_id": "#5120"}, dry_run=True)
assert preview == {"ok": True, "preview": "cancel #5120 (packing)", "reserved": False}
world.ship("5120")                                   # scripted: the courier takes it
result = tools.call(CANCEL_ORDER, world, ASHA, {"order_id": "5120"}, key=KEY)
assert result["error"] == "ALREADY_SHIPPED" and result["class"] == "business"
assert world.cancelled == [] and world.write_calls("cancel_order") == []
assert world.shipment("5120") == "in transit"        # nothing changed

# 2. The rest of the contract, on a fresh world.
world = World()
assert tools.call(CANCEL_ORDER, world, ASHA, {"order_id": "5120"})["error"] == "MISSING_KEY"
assert tools.call(CANCEL_ORDER, world, Session("c-42"), {"order_id": "5120"},
                  key=KEY)["error"] == "NOT_YOUR_ORDER"
assert tools.call(CANCEL_ORDER, world, ASHA, {"order_id": "51-20"},
                  key=KEY)["error"] == "BAD_ARGS"
first = tools.call(CANCEL_ORDER, world, ASHA, {"order_id": "5120"}, key=KEY)
again = tools.call(CANCEL_ORDER, world, ASHA, {"order_id": "5120"}, key=KEY)
assert first["ok"] and again["receipt"]["receipt_id"] == first["receipt"]["receipt_id"]
assert world.cancelled == ["5120"]                    # cancelled exactly once
print(f"preview: {preview['preview']}; after shipping: error={result['error']} "
      f"class={result['class']}; cancels in the world: {len(world.cancelled)}")
print("ch02 solution: OK")

"""Chapter 6 exercise: lose the response.

The payments mock applies the refund and drops the reply while a second worker retries.
The ledger holds UNKNOWN until reconcile reads the payments record; one payment, asserted
on the mock world, never on trace lines.
"""
import os
import tempfile

from _path import STUB  # noqa: F401

import ch06
import ledger
from world import World

path = os.path.join(tempfile.mkdtemp(), "ledger.db")
world = World(faults={"refund": ["LOST_REPLY"]})
w1, w2 = ledger.Ledger(path), ledger.Ledger(path)
seen = {}


def call(key):
    seen["worker2"] = w2.execute(ch06.OP, ch06.ARGS, ch06.refund_call(world),
                                 world.find_payment)["state"]
    return world.refund("2001", 950, key=key)


before = w1.execute(ch06.OP, ch06.ARGS, call, world.find_payment)["state"]
assert before == "UNKNOWN" and seen["worker2"] == "SUBMITTED"
after = w2.reconcile(ch06.OP, world.find_payment)["state"]
assert after == "CONFIRMED"
assert len(world.payments_for("2001")) == 1
assert w2.execute(ch06.OP, ch06.ARGS, ch06.refund_call(world),
                  world.find_payment)["receipt"]["receipt_id"] == world.payments[0]["receipt_id"]
assert len(world.payments_for("2001")) == 1

# the same guarantee when a model (stub or real) proposes the refund
model_world, model_world_events = ch06.model_drives()
assert len(model_world.payments_for("2001")) <= 1, "the ledger must never pay twice"
assert all(p["order_id"] == "2001" for p in model_world.payments)
replies = [e for e in model_world_events if e["kind"] == "reply"]
if not model_world.payments:      # no money moved: the reply must not say it did
    assert replies and replies[-1]["text"].startswith("escalate"), replies
if STUB:
    assert len(model_world.payments_for("2001")) == 1
print(f"before reconcile: {before}; after: {after}; payments for #2001: "
      f"{len(world.payments_for('2001'))}")
print("ch06 solution: OK")

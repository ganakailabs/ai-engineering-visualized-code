"""Implementation tests for Chapter 6: the six named ledger cases, on the mock world."""
import os
import tempfile

import _path  # noqa: F401

import ch06
import ledger
from world import World

OP, ARGS = ch06.OP, ch06.ARGS

# BREAK/FIX strip "The Timeout Retry"
assert len(ch06.timeout_retry_break().payments_for("2001")) == 2
world, again = ch06.ledger_fix()
assert len(world.payments_for("2001")) == 1 and again["state"] == "CONFIRMED"

# 1. lost response -> UNKNOWN -> reconcile -> CONFIRMED, one payment
w = World(faults={"refund": ["LOST_REPLY"]})
b = ledger.Ledger()
assert b.execute(OP, ARGS, ch06.refund_call(w), w.find_payment)["state"] == "UNKNOWN"
assert b.execute(OP, ARGS, ch06.refund_call(w), w.find_payment)["state"] == "CONFIRMED"
assert len(w.payments_for("2001")) == 1

# 1b. a timeout before the write: reconcile finds nothing, the same key is reused
w = World(faults={"refund": ["TIMEOUT"]})
b = ledger.Ledger()
first = b.execute(OP, ARGS, ch06.refund_call(w), w.find_payment)
assert first["state"] == "UNKNOWN" and w.payments == []
second = b.execute(OP, ARGS, ch06.refund_call(w), w.find_payment)
assert second["state"] == "CONFIRMED" and second["key"] == first["key"] and len(w.payments) == 1

# 2. two concurrent attempts: only one claim wins
path = os.path.join(tempfile.mkdtemp(), "l.db")
w, a, c = World(), ledger.Ledger(path), ledger.Ledger(path)
inner = {}
a.execute(OP, ARGS, lambda key: (inner.setdefault("c", c.execute(
    OP, ARGS, ch06.refund_call(w), w.find_payment)), w.refund("2001", 950, key=key))[1],
    w.find_payment)
assert inner["c"]["state"] == "SUBMITTED" and len(w.payments) == 1

# 3. changed arguments under one operation are refused
b = ledger.Ledger()
b.prepare(OP, ARGS)
try:
    b.prepare(OP, dict(ARGS, amount=9500))
    raise AssertionError("changed args must be refused")
except ledger.ArgsChanged:
    pass
assert ledger.key_for(OP, ARGS) != ledger.key_for(OP, dict(ARGS, amount=9500))

# 4. a restart: a new process reads the same ledger file
path = os.path.join(tempfile.mkdtemp(), "l.db")
w = World(faults={"refund": ["LOST_REPLY"]})
ledger.Ledger(path).execute(OP, ARGS, ch06.refund_call(w), w.find_payment)
assert ledger.Ledger(path).row(OP)["state"] == "UNKNOWN"
assert ledger.Ledger(path).execute(OP, ARGS, ch06.refund_call(w),
                                   w.find_payment)["state"] == "CONFIRMED"
assert len(w.payments_for("2001")) == 1

# 5. the receiver's key expired: reconcile reads the payments record, no second payment
assert len(ch06.expired_key(False).payments_for("2001")) == 2      # BREAK, documented
assert len(ch06.expired_key(True).payments_for("2001")) == 1       # FIX

# 6. compensation: works, fails to NEEDS_HUMAN, and a paid refund cannot be undone
w, b = ch06.compensation()
assert b.row("op-pickup-2001")["state"] == "COMPENSATED" and w.pickups == []
assert w.stock["mug set green"] == 4                               # the unit is back
w, b = ch06.compensation("ALREADY_COLLECTED")
assert b.row("op-pickup-2001")["state"] == "NEEDS_HUMAN" and len(w.pickups) == 1
assert b.row(OP)["state"] == "NEEDS_HUMAN" and len(w.payments_for("2001")) == 1
print("test_ledger: OK")

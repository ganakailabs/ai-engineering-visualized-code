"""Chapters 5-6: process death. A hard exit runs no except or finally block, so
recovery has to come from durable records read by a fresh process."""
import json
import os
import subprocess
import sys
import tempfile

import _path  # noqa: F401

import ledger
import state

OP, ARGS = "op-refund-2001", {"order_id": "2001", "amount": 950}
HERE = os.path.dirname(os.path.abspath(__file__))


def child(code):
    """Run code in a fresh interpreter that dies with os._exit(71)."""
    pre = f"import sys; sys.path.insert(0, {HERE!r}); import _path, ledger, state, os, json\n"
    rc = subprocess.call([sys.executable, "-c", pre + code])
    assert rc == 71, rc


def marker_find(path):
    """The receiver's authoritative record: a file that outlives the process."""
    def find(key):
        if os.path.exists(path):
            rec = json.load(open(path))
            return rec if rec["key"] == key else None
        return None
    return find


# --- Ch 6, crash 1: the worker dies inside the call, before any effect ---
d = tempfile.mkdtemp()
db, marker = os.path.join(d, "l.db"), os.path.join(d, "remote.json")
child(f"ledger.Ledger({db!r}).execute({OP!r}, {ARGS!r}, lambda key: os._exit(71), "
      f"lambda key: None)")
assert ledger.Ledger(db).row(OP)["state"] == "SUBMITTED"
calls, finds = [], []
find = marker_find(marker)


def call(key):
    calls.append(key)
    json.dump({"key": key, "receipt_id": "pay-001"}, open(marker, "w"))
    return {"receipt_id": "pay-001"}


def counted_find(key):
    finds.append(key)
    return find(key)


fresh = ledger.Ledger(db, lease_s=0)          # the dead worker's lease has run out
assert fresh.abandoned() == [OP]
row = fresh.execute(OP, ARGS, call, counted_find)
assert finds, "an abandoned SUBMITTED row must be reconciled before any retry"
assert row["state"] == "CONFIRMED" and len(calls) == 1

# --- Ch 6, crash 2: the remote effect landed, then the worker died ---
d = tempfile.mkdtemp()
db, marker = os.path.join(d, "l.db"), os.path.join(d, "remote.json")
child(f"""
def call(key):
    json.dump({{"key": key, "receipt_id": "pay-001"}}, open({marker!r}, "w"))
    os._exit(71)
ledger.Ledger({db!r}).execute({OP!r}, {ARGS!r}, call, lambda key: None)""")
calls = []
row = ledger.Ledger(db, lease_s=0).execute(OP, ARGS, call, marker_find(marker))
assert row["state"] == "CONFIRMED" and calls == [], "found by reconcile: no second call"
assert row["receipt"]["receipt_id"] == "pay-001"

# --- a live claim inside its lease is left alone (no second worker steals it) ---
d = tempfile.mkdtemp()
db = os.path.join(d, "l.db")
child(f"ledger.Ledger({db!r}).execute({OP!r}, {ARGS!r}, lambda key: os._exit(71), "
      f"lambda key: None)")
assert ledger.Ledger(db, lease_s=3600).abandoned() == []
assert ledger.Ledger(db, lease_s=3600).execute(OP, ARGS, call, lambda k: None)["state"] == \
    "SUBMITTED"

# --- a lookup that cannot answer keeps the operation UNKNOWN (no blind retry) ---
def outage(key):
    raise ledger.LookupUnavailable("payments API down")


b = ledger.Ledger(lease_s=0)
b.prepare(OP, ARGS)
b._move(OP, "PREPARED", "SUBMITTED")
calls = []
assert b.execute(OP, ARGS, call, outage)["state"] == "UNKNOWN" and calls == []
# without a receiver contract, "not found" is not proof it never landed
b = ledger.Ledger(lease_s=0, absent_means_not_applied=False)
b.prepare(OP, ARGS)
b._move(OP, "PREPARED", "SUBMITTED")
assert b.execute(OP, ARGS, call, lambda k: None)["state"] == "UNKNOWN" and calls == []

# --- Ch 5: a worker killed mid-run leaves an attempt record a fresh worker recovers ---
d = tempfile.mkdtemp()
db = os.path.join(d, "t.db")
child(f"""
s = state.Store({db!r}); s.create("T-1")
class T:
    def emit(self, *a, **k): pass
state.run_loop(s, "T-1", lambda c: os._exit(71), lambda m: "", T(), lambda: False)""")
s = state.Store(db)
assert s.stop_record("T-1") is None, "finally did not run: no stop was written"
assert s.abandoned() == ["T-1"]
assert state.recover(s) == ["T-1"]
assert s.stop_record("T-1")["reason"] == "needs_human" and s.load("T-1")[0] == "HANDOFF"
assert s.abandoned() == []
print("test_recovery: OK")

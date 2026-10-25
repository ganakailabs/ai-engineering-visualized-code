"""Chapter 9 exercise: withdraw consent.

Asha withdraws consent. Her persistent and episodic memory goes from the store, the
index and the summaries. The refund ledger is not memory: it stays.
"""
from _path import STUB

import ch09

world, m, tr = ch09.correction(propagate=True)
world.refund("2001", 950, key="k-T-2001-a-refund-2001")      # a refund in the ledger
before = len(world.payments)
gone = m.forget("asha")
r = m.recall("asha")
tr.emit("memory", f"forget scope=asha -> deleted {gone}; recall episodes={len(r['episodes'])}")
assert r["episodes"] == [] and r["facts"] == [] and r["summary"] == ""
assert not any(rec["scope_id"] == "asha" for rec in m.store.values())
assert all(ch09.OLD.lower() not in t and ch09.NEW.lower() not in t for t in m.index.values())
assert "asha" not in m.summaries
assert len(world.payments) == before == 1, "the refund ledger is not memory"
assert m.recall("team")["facts"], "team memory is another scope; it stays"

# the model's reply after a correction: the context it is given never holds the old address
world, m, tr = ch09.correction(propagate=True)
context, reply = ch09.model_replies(m, tr)
assert ch09.NEW in context and ch09.OLD not in context
assert "Koregaon" not in reply, "the corrected address must never come back"
if STUB:
    assert ch09.NEW in reply
print(f"deleted {gone} records; episodes now {len(r['episodes'])}; payments kept: {before}")
print("ch09 solution: OK")

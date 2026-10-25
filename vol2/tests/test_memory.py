"""Implementation tests for Chapter 9: a corrected fact never returns; deletion is total."""
import _path  # noqa: F401

import ch09

world, m, tr = ch09.correction(propagate=False)                  # BREAK, documented
assert m.copies_of(ch09.OLD) == {"store": False, "index": True, "summary": True}
assert ch09.OLD in m.recall("asha")["summary"]

world, m, tr = ch09.correction(propagate=True)                   # FIX
assert m.copies_of(ch09.OLD) == {"store": False, "index": False, "summary": False}
assert m.recall("asha", "address")["facts"][0]["value"] == ch09.NEW
old = [r for r in m.store.values() if r["value"] == ch09.OLD][0]
assert old["superseded_by"] and old["source"] == "ticket-T-1873"  # history and provenance
new = m.store[old["superseded_by"]]
assert new["source"] == "ticket-T-2001-a" and new["lifetime"] == "persistent"

# lifetime: the session record expires on schedule, in every copy
assert m.recall("T-2001-a")["facts"]
ch09.lifetimes(m, tr)
assert m.recall("T-2001-a")["facts"] == [] and "waiting on the phone" not in str(m.index)

# permissions: a team note is for agents, not for the customer's own view
assert m.recall("team", reader="agent")["facts"] and not m.recall("team", reader="asha")["facts"]

# deletion reaches the store, the index and the summaries
m.forget("asha")
assert m.copies_of(ch09.NEW) == {"store": False, "index": False, "summary": False}
assert m.recall("asha")["episodes"] == []
print("test_memory: OK")

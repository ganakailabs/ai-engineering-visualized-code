"""Chapter 11 exercise: ask two things at once (scenario SC-007, EU customer).

An EU customer asks about the unused desk lamp from #1234 and about return shipping.
The agent must split the question, fill every slot from evidence it retrieved, and stay
within 1 + 2 retrieval rounds. #1234 was delivered 2026-08-24, 41 days before TODAY.
"""
from _path import STUB

import agentic_rag as rag
import ch11

EU = {"customer_id": "asha", "region": "EU"}          # fixture addition (SC-007)
Q = ("I am in the EU. Can I return the unused desk lamp from #1234, "
     "and who pays shipping?")

r = rag.agentic(Q, EU, ch11.stub_agent)
assert r["rounds"] <= 1 + rag.EXTRA_ROUNDS, r["rounds"]
assert set(r["cites"]) <= set(r["evidence"]), "cites only retrieved passages"
# strict: a handoff is not a solution, on the stub or on a real model
assert r["reason"] == "success", f"stopped with {r['reason']}: {r['reply']}"
assert set(r["cites"]) == {"R1", "S5", "S3"}, r["cites"]
assert "declined" in r["reply"] and "paid by the customer" in r["reply"]
if STUB:
    subs = r["trace"].of("decompose")
    assert len(subs) == 2, subs
    assert r["rounds"] == 3
print(f"rounds={r['rounds']} cites={r['cites']} stop={r['reason']}")
print("ch11 solution: OK")

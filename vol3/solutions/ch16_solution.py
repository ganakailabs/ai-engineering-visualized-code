"""Chapter 16 exercise: pass the knowledge exam (graduation).

Run the Vol 3 held-out benchmark: conflicts, permissions, outdated records,
tables, multi-hop and expected abstains. Predict first: which stage fails
first if you skip precedence? The conflict cases.
"""
import _path  # noqa: F401

import gate as G

full = G.gate("baseline", "chunking_fixed")
assert full["verdict"] == "pass" and not full["critical"]
assert full["answered"] / full["answerable"] >= G.MIN_ANSWER_RATE
assert full["abstained"] == full["expected_abstain"]
print(f"graduation  answered={full['answered']}/{full['answerable']} "
      f"abstained={full['abstained']}/{full['expected_abstain']} -> pass")

lazy = G.gate("baseline", "abstain_all")
assert lazy["verdict"] == "blocked" and lazy["answered"] == 0
print(f"abstain_all answered=0/{lazy['answerable']} -> blocked")

skip = G.gate("baseline", "no_precedence")
cats = sorted({G.CAT[c] for c in skip["critical"]})
print(f"no_precedence critical={skip['critical']} categories={cats} -> {skip['verdict']}")
assert skip["verdict"] == "blocked" and cats == ["conflicts"]

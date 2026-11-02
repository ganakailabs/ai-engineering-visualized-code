"""Chapter 16 exercise: pass the knowledge exam (graduation).

Run the Vol 3 held-out benchmark: conflicts, permissions, outdated records,
tables, multi-hop and expected abstains. Predict first: which stage fails
first if you skip precedence? The conflict cases.

Part 2: three outcomes, three labels. For the chunking_fixed change, predict each of:
minimum quality passed? no new regression found? improvement demonstrated? Then drop
one case from the change's results, and separately make one noncritical case fail, and
predict the verdict each time.
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

g = G.gate("baseline", "chunking_fixed")
assert g["verdict"] == "pass" and g["new_failures"] == [] and not g["win"]
print(f"chunking_fixed: minimum quality passed=yes, new regressions={len(g['new_failures'])}, "
      f"improvement demonstrated={'yes' if g['win'] else 'no'} -> {g['label']}")
base, new = G.results("baseline"), G.results("chunking_fixed")
drop = dict(new)
gone = sorted(drop)[0]
del drop[gone]
m = G.gate_results(base, drop)
assert m["verdict"] == "blocked" and m["missing"] == [gone]
print(f"one case missing ({gone}): {m['verdict']}; {m['reasons'][0]}")
victim = next(c for c, _, _, critical in G.BENCH if not critical and base[c][0] and new[c][0])
worse = dict(new)
worse[victim] = (False, False)
w = G.gate_results(base, worse)
assert w["verdict"] == "blocked" and w["new_failures"] == [victim] and not w["critical"]
print(f"one noncritical new failure ({victim}): {w['verdict']}; "
      f"MAX_NEW_FAILURES={G.MAX_NEW_FAILURES}")
print("ch16 solution: OK")

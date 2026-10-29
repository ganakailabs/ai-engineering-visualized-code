"""Chapter 16: RAG Test Sets and Regression Gates (volume finale).

Run from the repo root:  python3 vol3/ch16.py
A scripted generator proposes questions; code review rejects bad ones; a hash
holds part back. Then the regression gate on the held-out benchmark: a chunking
change that lifts the mean but breaks the EU withdrawal case is blocked, an
abstain-everything system fails, and the fixed change passes with no regression
found (not a demonstrated win). Systems are
scripted results (a demonstration). No model is used.
"""
import _root  # noqa: F401

import gate as G

ok, bad = G.review()
dev, held = G.split(ok)
print(f"generated={len(G.PROPOSED)} approved={len(ok)} dev={len(dev)} held_out={len(held)}")
for q, why in bad:
    print(f"  rejected  {why:30} {q}")
base = G.results("baseline")
print(f"baseline  correct={sum(v[0] for v in base.values())}/{len(G.BENCH)}")
for name in ("chunking_change", "abstain_all", "chunking_fixed"):
    g = G.gate("baseline", name)
    lo, hi = g["interval"]
    print(f"gate {name:16} mean={g['mean']:.2f} paired diff={g['diff']:+.3f} "
          f"interval=[{lo:+.3f}, {hi:+.3f}] win={g['win']}")
    print(f"     answered={g['answered']}/{g['answerable']} "
          f"abstained={g['abstained']}/{g['expected_abstain']} "
          f"critical={g['critical'] or 'none'} -> {g['label']}"
          + (f" ({'; '.join(g['reasons'])})" if g["reasons"] else ""))

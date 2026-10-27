"""Chapter 7 exercise: tell the twins apart.

Query 'nw550 battery'. Predict which methods return the NW-500 chunk first, then check:
every fusion without the exact lane picks the twin; the exact lane picks NW-550.
"""
import _path  # noqa: F401

import hybrid as H

Q = "nw550 battery"
for m in ("words", "meaning", "rrf", "score"):
    top = H.search(Q, m, lane=False)[0]
    assert top == "nw500-batt", (m, top)
    print(f"{m:8} no lane -> {top}")
top = H.search(Q, "score", w=H.tune())[0]
assert top == "nw550-batt"
print(f"score + exact lane -> {top}")
print("ch07 solution: OK")

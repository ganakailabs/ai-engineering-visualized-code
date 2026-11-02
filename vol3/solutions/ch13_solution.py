"""Chapter 13 exercise: three kinds of answer.

Add one covered part, one explicitly excluded part and one part with no edge.
Predict first: what does each return? Only an explicit edge can say no.

Part 2: predict, then shuffle. Shuffle the edge list twenty times with a fixed seed.
Does any coverage answer change? It must not: an answer that depends on edge order is
a bug in the walk, not a fact about the parts.
"""
import random

import _path  # noqa: F401

import graph as G

G.ALIASES.update({"nw pouch": "NW-500 pouch", "nw foam tips": "NW-500 foam tips",
                  "nw stand": "NW-500 stand"})
G.EDGES += [("NW-500 pouch", "PART_OF", "NW-500 Travel Bundle", "catalogue p.4 bundle contents"),
            ("NW-500 foam tips", "EXCLUDES", "W2 bundle warranty", "policy W2.3 wear parts excluded")]
want = {"nw pouch": "covered", "nw foam tips": "excluded", "nw stand": "unknown"}
for part, expected in want.items():
    verdict, hops = G.coverage(part)
    assert verdict == expected, (part, verdict)
    assert all(h[3] for h in hops)                     # every edge cites a source
    print(f"{part:13} coverage {verdict}" + ("  -> escalate" if verdict == "unknown" else
                                             f"  source={hops[-1][3]}"))

base = {part: G.coverage(part) for part in want}
rng = random.Random(7)
changed = 0
for _ in range(20):
    edges = list(G.EDGES)
    rng.shuffle(edges)
    changed += sum(G.coverage(part, edges=edges) != base[part] for part in want)
assert changed == 0
print(f"shuffled edges 20 times: answers changed={changed}")
print("ch13 solution: OK")

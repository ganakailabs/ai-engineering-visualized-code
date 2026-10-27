"""Chapter 13: Knowledge Graphs and Multi-Hop Retrieval.

Run from the repo root:  python3 vol3/ch13.py
Resolve two names to one product, follow cited edges, and tell covered, excluded and
unknown apart. Then the same question as one SQL join. No model is used.
"""
import _root  # noqa: F401

import graph as G

if __name__ == "__main__":
    print("Part 1 (MM-087): entities and edges")
    for name in ("NW charger", "USB-C charger (NW)"):
        print(f'  resolve "{name}" = "{G.resolve(name)}"')

    print("\nPart 2 (MM-088): the multi-hop path")
    for part in ("NW charger", "NW-500 ear tips", "NW-500 cable"):
        verdict, hops = G.coverage(part)
        print(f"  question: is {part} covered by the bundle warranty?")
        for n, (a, rel, b, src) in enumerate(hops, 1):
            print(f"    hop {n} {a} -{rel}-> {b}  source={src}")
        print(f"    coverage {verdict}")
        if verdict == "unknown":
            print(f"    escalate  no edge, no clause  (naive reading: {G.naive_coverage(part)})")

    print("\nTry a join first:")
    for row in G.join_bundle("NW charger"):
        print(f"  join  warranty={row[0]}  sources={row[1]}; {row[2]}")

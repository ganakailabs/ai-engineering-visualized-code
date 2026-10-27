"""Chapter 7: Hybrid Search: Keywords Plus Meaning.

Run from the repo root:  python3 vol3/ch07.py
An exact-match lane for product codes, rank fusion vs score fusion, and a weight
chosen on the dev split and reported on the held-out split. No model is used; the
meaning lane is the Ch 6 toy embedder "gram-v1".
"""
import _root  # noqa: F401

import hybrid as H


def fmt(r):
    return " ".join(f"{t}={h}/{n}" for t, (h, n) in sorted(r.items()))


if __name__ == "__main__":
    print("Part 1 (MM-077): the analyzer and the exact lane")
    q = "nw500"
    print(f"  analyze({q!r})={H.analyze(q)}  words top={H.search(q, 'words', lane=False)[0]}")
    hits, ids = H.exact_lane(q)
    print(f'  lane exact matched={ids[0]} (from "{q}") chunks={hits}')

    print('\nPart 2 (MM-078): top 3 for "the nw-550 won\'t pair", no lane')
    q = "the nw-550 won't pair"
    for m in ("words", "meaning", "rrf", "score"):
        print(f"  {m:8} {H.search(q, m, lane=False)[:3]}")

    print("\nPart 3: weight chosen on DEV, reported on HELD-OUT (recall@1 by type, exact lane on)")
    w = H.tune()
    print(f"  chosen w={w} (words weight; meaning gets {1 - w})")
    for name, kw in (("words", {"method": "words"}), ("meaning", {"method": "meaning"}),
                     ("rrf", {"method": "rrf"}), (f"score w={w}", {"w": w})):
        print(f"  {name:12} dev {fmt(H.recall_by_type(H.DEV, **kw))}"
              f"  held-out {fmt(H.recall_by_type(H.HELD_OUT, **kw))}")

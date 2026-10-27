"""Chapter 4: Structure-Aware Chunking and Applicability Metadata.

Run from the repo root:  python3 vol3/ch04.py
The returns handbook (vol3/knowledge/policy/) is a fictional fixture. No model is used:
Part 1 is the fixed-size cut, Part 2 the heading cut with small-to-big, Part 3 the
applicability gate on the pinned date (store.TODAY = 2026-10-04).
"""
import _root  # noqa: F401

import chunking as C

Q = "My mug arrived broken. What do I need to send?"

if __name__ == "__main__":
    meta, body = C.read()
    print("Part 1 (MM-072 Break): 12-word chunks")
    cuts = C.fixed_chunks(body)
    for c in cuts:
        if "photo" in c or "7 days" in c:
            print(f"  {c!r}")
    naive = max(cuts, key=lambda c: len(C.words(Q) & C.words(c)))
    print(f"  best match for the mug question: {naive!r}")

    print("\nPart 2 (MM-072, MM-073 Fix): heading chunks, small to find, big to read")
    parents = C.section_chunks(meta, body)
    print(f"  sections={len(parents)} small={len(C.small_chunks(parents))}")
    r = C.answer_context(Q, product="mug", region="IN")
    print(f"  handed over: {r['parent']['text']!r}")

    print("\nPart 3 (MM-074): what applies to Asha (product=mug region=IN)")
    print(f"  kept: {[k.split(':')[1] for k in r['kept']]}")


def overlap_demo():
    """Sidebar SB-v3-04: overlap costs storage and still cuts by count, not by rule."""
    meta, body = C.read()
    print("\nPart 4 (sidebar): the overlap trade-off, 12-word chunks")
    for ov in (0, 6):
        cs = C.fixed_chunks(body, 12, ov)
        both = any("7 days" in c and "photo" in c for c in cs)
        print(f"  overlap={ov}  chunks={len(cs)} words_stored={sum(len(c.split()) for c in cs)}"
              f"  '7 days'+'photo' together={'yes' if both else 'no'}")


if __name__ == "__main__":
    overlap_demo()

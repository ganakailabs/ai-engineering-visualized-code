"""Chapter 6: Embedding Models and Vector Indexes.

Run from the repo root:  python3 vol3/ch06.py
Two toy embedders (standard library, fictional) on the six-question retrieval golden set,
then an IVF-style clustered index against exact search, then the embedding contract.
Real embedders: see vol3/runs/README.md (Chapter 6).
"""
import os

import _root  # noqa: F401

import vectors as V

if __name__ == "__main__":
    print("Part 1 (MM-075): two embedders on your own questions (recall@1)")
    extra = [f"ollama:{m}" for m in os.environ.get("AIEV_EMBED", "").split(",") if m]
    for m in ["lexi-v1", "gram-v1"] + extra:     # e.g. AIEV_EMBED=nomic-embed-text
        h, n = V.recall_at(m, 1)
        print(f"  {m}: {h}/{n}")

    print("\nPart 2 (MM-076): clustered index vs exact search, k=1, probe=1")
    ix = V.ClusteredIndex()
    qs = [q for q, _ in V.GOLDEN]
    found, total, compared, missed = V.ann_recall(ix, qs, k=1, probe=1)
    print(f"  groups={len(ix.groups)} ann_recall@1 vs exact={found}/{total}")
    print(f"  vectors_compared exact={len(qs) * len(ix.vecs)} ann={compared}")
    for q, d in missed:
        print(f"  missed neighbour: {q!r} -> {d}")

    print("\nPart 3: the contract")
    try:
        ix.query("pair my NW-550", V.contract("gram-v1", "v2"))
    except ValueError as e:
        print(f"  contract embedder=v2 index=v1 -> refused ({e})")

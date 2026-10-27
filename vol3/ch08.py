"""Chapter 8: Reranking: The Second Opinion.

Run from the repo root:  python3 vol3/ch08.py
Retrieve wide with the cheap Ch 6 embedder, rerank to 5. The default reranker is a
scripted DEMONSTRATION scorer, not a model. Set AIEV_RERANKER to a cross-encoder name
to run a real one (vol3/runs/README.md); those numbers are [TO MEASURE] in the book.
"""
import _root  # noqa: F401

import rerank as R

if __name__ == "__main__":
    score = R.scorer()
    q = "what is the return window"
    print(f'Part 1 (MM-079): "{q}"')
    pool = R.first_stage(q, 40)
    print(f"  first stage top 5: {pool[:5]}")
    print(f"  ret-window first-stage rank={pool.index('ret-window') + 1}")
    print(f"  reranked top 5 from net 20: {R.rerank(q, R.first_stage(q, 20), 5, score)}")

    print("\nPart 2 (MM-080): recall over the 8 golden questions")
    print(f"  first stage alone, top 5: {'%d/%d' % R.recall(5, reranked=False)}")
    for k in (5, 10, 20, 30, 40):
        fk, rk = R.recall(k, reranked=False), R.recall(k, score=score)
        print(f"  net={k:2}  first-stage recall@{k}={fk[0]}/{fk[1]}"
              f"  reranked recall@5={rk[0]}/{rk[1]}  reranker calls={k * len(R.GOLDEN)}")
        assert rk[0] <= fk[0]          # reranking cannot find what the net missed

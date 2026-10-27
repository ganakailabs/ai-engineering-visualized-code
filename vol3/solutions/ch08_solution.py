"""Chapter 8 exercise: find the smallest net.

Predict the smallest first-stage net k whose reranked recall@5 is as good as any net.
Then check: k=20 gives 7/8, the same as 30 and 40, at half the reranker calls of 40.
"""
import _path  # noqa: F401

import rerank as R

best = max(R.recall(k)[0] for k in (5, 10, 20, 30, 40))
smallest = min(k for k in (5, 10, 20, 30, 40) if R.recall(k)[0] == best)
assert (smallest, best) == (20, 7), (smallest, best)
print(f"smallest net={smallest} reranked recall@5={best}/8 calls={smallest * 8}")
print("ch08 solution: OK")

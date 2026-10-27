"""Chapter 6 exercise: search one more cluster.

Raise the groups searched from 1 to 2. Predict ANN recall and vectors compared first;
then assert both as counts (never wall-clock time).
"""
import _path  # noqa: F401

import vectors as V

ix = V.ClusteredIndex()
qs = [q for q, _ in V.GOLDEN]
one = V.ann_recall(ix, qs, k=1, probe=1)
two = V.ann_recall(ix, qs, k=1, probe=2)
assert one[0] < one[1] and two[0] == two[1]          # reaches the exact result
assert one[2] < two[2] < len(qs) * len(ix.vecs)       # more work, still under exact
print(f"probe=1 recall={one[0]}/{one[1]} compared={one[2]}")
print(f"probe=2 recall={two[0]}/{two[1]} compared={two[2]}")
print("ch06 solution: OK")

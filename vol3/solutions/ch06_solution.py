"""Chapter 6 exercise: search one more cluster.

Raise the groups searched from 1 to 2. Predict ANN recall and candidates scored first;
then assert both as counts (never wall-clock time).
"""
import _path  # noqa: F401

import vectors as V

ix = V.ClusteredIndex()
qs = [q for q, _ in V.GOLDEN]
one = V.ann_recall(ix, qs, k=1, probe=1)
two = V.ann_recall(ix, qs, k=1, probe=2)
assert one[0] < one[1] and two[0] == two[1]          # reaches the exact result
assert one[2] < two[2] < len(qs) * len(ix.vecs)       # more candidates, still under exact
assert one[3] == two[3] == len(qs) * len(ix.centroids)  # routing cost is the same
print(f"probe=1 recall={one[0]}/{one[1]} candidates_scored={one[2]} routing={one[3]}")
print(f"probe=2 recall={two[0]}/{two[1]} candidates_scored={two[2]} routing={two[3]}")
print("ch06 solution: OK")

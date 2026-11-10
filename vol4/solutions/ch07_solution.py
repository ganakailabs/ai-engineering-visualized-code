"""Chapter 7 exercise: Slow the reranker.

A new reranker is three times slower: 120 ms becomes 360 ms. Predict first: does the
ticket get slower, and by how much?

The reranker runs in parallel with the order lookup. Retrieve + rerank took 370 ms
against the lookup's 520 ms, so it had 150 ms of slack. At 360 ms the branch takes
610 ms, uses up the slack, and becomes the critical path: the total grows by 90 ms,
not by the 240 ms added to the reranker. Durations are simulated.
"""
import _path  # noqa: F401

import latency as L

start, end = L.schedule(L.STEPS)
before = L.to_spans(start, end)
start, end = L.schedule(L.STEPS, overrides={"rerank": {"ms": 360}})
after = L.to_spans(start, end)
path = L.critical_path(after)
grew = L.total_ms(after) - L.total_ms(before)
print(f"rerank 120 -> 360 ms: total {L.total_ms(before):.0f} -> {L.total_ms(after):.0f} ms "
      f"(+{grew:.0f}, simulated)")
print("critical: " + " > ".join(path[2:5]) + " > ...")
assert "rerank" in path and "order_lookup" not in path
assert grew == 90
print("ch07 solution: OK")

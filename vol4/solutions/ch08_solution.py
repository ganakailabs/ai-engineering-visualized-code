"""Chapter 8 exercise: Flood the queue.

Send three times the simulated peak (90 tickets a minute for 10 minutes) to the bounded
queue sized in the chapter (8 workers, 12 s per ticket, 60 s deadline). Predict first:
how many tickets are refused, and are any accepted ones lost?

The workers finish 40 tickets a minute, so in 10 minutes they take 400 plus the 32 the
queue may hold. Everything else is refused with a retry signal. Every admitted ticket
finishes exactly once and inside the deadline. All arrivals are simulated.
"""
import _path  # noqa: F401

from collections import Counter

import stream as S

out, done = S.simulate(90, 10, workers=8, service_s=12, deadline_s=60)
admitted = [t for t, o in out.items() if o["admitted"]]
refused = [t for t, o in out.items() if not o["admitted"]]
lost = set(admitted) - set(done)
dup = [t for t, n in Counter(done).items() if n > 1]
worst = max(out[t]["reply_s"] for t in admitted)
print(f"3x peak, simulated: arrived={len(out)} "
      f"admitted={len(admitted)} refused={len(refused)}")
print(f"refused with retry_after: {sum('retry_after_s' in out[t] for t in refused)}; "
      f"accepted lost: {len(lost)}; duplicated: {len(dup)}")
print(f"worst reply {worst} s (deadline 60 s)")
assert len(admitted) == 432 and len(refused) == 468
assert all("retry_after_s" in out[t] for t in refused)
assert not lost and not dup and worst <= 60
print("ch08 solution: OK")

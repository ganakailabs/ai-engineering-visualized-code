"""Chapter 4 exercise: Watch the new slice.

From day 10, gift-card tickets arrive (scenario SC-014, clause S4: gift cards
cannot be exchanged for cash), about 10 a day (simulated). Predict first: what
does plan v1 do with them, and what should the drift watch say on a slice that
has no baseline?

Plan v1 has fixed strata, so the new slice is reported as unplanned and never
scored. Plan v2 adds a gift_card stratum (a recorded change to the plan, version
2). The drift watch has no week-1 baseline for it, so it does not compare: it
says so and asks for a review, with the interval it has so far.
"""
import _path  # noqa: F401

import ch04
import shadow as S
import traffic

tickets = traffic.live(extra={"gift_card": (10, 10)})
v1 = S.plan(["refund", "delivery", "final_sale"])
daily, tot = ch04.run(tickets, v1)
print(f"plan v1: unplanned slices={sorted(tot['unplanned'])} (not scored)")

v2 = S.plan(["refund", "delivery", "final_sale", "gift_card"], version=2)
daily, tot = ch04.run(tickets, v2)
print(f"plan v2 strata={','.join(v2['strata'])}: unplanned={sorted(tot['unplanned'])}")
d = S.drift(daily["gift_card"], ch04.BASELINE, range(10, 15))
r = d["recent"]
print("drift policy_cited slice=gift_card baseline=none (new slice)")
print(f"  days 10-14={r['rate']:.2f} [{r['lo']:.2f},{r['hi']:.2f}] n={r['n']} "
      f"-> alert: review")
assert d["base"] is None and d["alert"] == "new slice, no baseline"
assert tot["unplanned"] == set()
print("ch04 solution: OK")

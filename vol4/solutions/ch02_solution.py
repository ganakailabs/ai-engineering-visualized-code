"""Chapter 2 exercise: Add a resolution SLO.

"Resolved without a reopen within 7 days." The outcome is delayed: a ticket is not
eligible until it is 7 days old, because before then nobody knows whether it will be
reopened. Predict first: which tickets are not yet eligible today?

Eligible: non-probe, non-cancelled tickets at least 7 simulated days old.
Good: eligible and not reopened. Target: 95.0% (the lab's choice).
"""
import _path  # noqa: F401

import slo
import traffic

WAIT_DAYS, TARGET = 7, 950
week = traffic.week()


def eligible_resolution(t):
    return slo.eligible_latency(t) and t["age_days"] >= WAIT_DAYS


events = [t for t in week if eligible_resolution(t)]
waiting = [t for t in week if slo.eligible_latency(t) and t["age_days"] < WAIT_DAYS]
good = sum(1 for t in events if not t["reopened"])
b = slo.budget(len(events), good, TARGET)

by_day = {}
for t in waiting:
    by_day[t["day"]] = by_day.get(t["day"], 0) + 1
print(f"not yet eligible (younger than {WAIT_DAYS} days): {len(waiting)} tickets")
print("  " + ", ".join(f"{d} {n}" for d, n in by_day.items()))
print(f"slo resolution eligible={b['eligible']} good={b['good']} "
      f"target={TARGET / 10:.1f}%")
print(f"  allowed_bad={b['allowed_bad']} used={b['bad']} (simulated)")

# hand counts, done a second way: walk the Monday tickets one by one
mon = [t for t in week if t["day"] == "Mon"]
n_elig = n_good = 0
for t in mon:
    if t["tenant_id"] == "probe" or t["cancelled"]:
        continue
    n_elig += 1
    n_good += 0 if t["reopened"] else 1
assert (b["eligible"], b["good"]) == (n_elig, n_good)
assert b["allowed_bad"] == n_elig * 50 // 1000
assert all(t["day"] != "Mon" for t in waiting)           # only Monday is 7 days old
assert "Tue" in by_day and "Sun" in by_day
print("ch02 solution: OK")

"""Implementation test for Chapter 4: copies only, counted failures, interval drift."""
import _path  # noqa: F401

import ch04
import shadow as S
import traffic

tickets = traffic.live()
before = S.fingerprint(tickets)
daily, tot = ch04.run(tickets, S.plan(["refund", "delivery", "final_sale"]))
assert S.fingerprint(tickets) == before and "weight" not in tickets[0]
assert tot["failed"] == sum(t["malformed"] for s in daily.values() for d in s.values()
                            for t, _ in d)
# the pooled refund window alerts; delivery, which did not move, does not
assert ch04.first_alert(daily["refund"])[0] is not None
assert ch04.first_alert(daily["delivery"])[0] is None
lo, hi = S.wilson(0, 0)
assert (lo, hi) == (0.0, 1.0) and S.wilson(10, 10)[1] == 1.0
# coverage gate: a grader that fails mostly on the hard (wrong) refund replies makes the
# refund rate look better; the gate withholds the slice instead of publishing it
graded = [g for sl in daily.values() for d in sl.values() for g in d]
selective = [(t, None if (t["slice"] == "refund" and r is False) else r) for t, r in graded]
honest = S.score(graded, "refund")["rate"]
flattered = S.score(selective, "refund")["rate"]
assert flattered > honest
cov = S.coverage(selective, ["refund", "delivery", "final_sale"])
assert cov["refund"][1] is False and cov["delivery"][1] is True
assert all(ok for _, ok in S.coverage(graded, ["refund", "delivery", "final_sale"]).values())
print("test_shadow: OK")

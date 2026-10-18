"""Chapter 24 exercise: fail on purpose.

1. Make the provider rate-limit twice, then answer. How long did you wait?
2. Make it send a bad request. How many tries, and why?
3. Raise the model's time to 3,000 ms. Which box breaks the budget?
Run: python3 solutions/ch24_solution.py
"""
import _path  # noqa: F401
from ch24 import GIVE_UP, TIMINGS, RefundService, call_with_retry, flaky, over_budget, refund_with_retry

Q = "My NW-500 battery stopped charging. Is it under warranty?"

if __name__ == "__main__":
    waits, lines = [], []
    ok = call_with_retry(flaky(["rate_limit", "rate_limit"]), Q,
                         sleep=waits.append, log=lines.append)
    print("waited", sum(waits), "s ->", ok[:40])
    lines.clear()
    bad = call_with_retry(flaky(["bad_request"]), Q,
                          sleep=waits.append, log=lines.append)
    print("bad request:", lines, "->", bad)
    slow = dict(TIMINGS, model=3000)
    print("slow model:", over_budget(slow))
    assert ok.startswith("answer:") and waits == [1.0, 2.0]
    assert bad == GIVE_UP and len(lines) == 1
    assert over_budget(slow) == (3250, "model", True)
    for key, n in ((None, 2), ("refund-3100-ticket-88", 1)):
        svc = RefundService()
        refund_with_retry(svc, "3100", 12500, key=key)
        print("lost reply, key", key, "->", len(svc.paid), "payment(s)")
        assert len(svc.paid) == n
    t = iter([0.0, 0.0, 29.5])          # a fake clock: the deadline is near
    late = call_with_retry(flaky(["timeout"] * 3), Q, sleep=lambda s: None,
                           clock=lambda: next(t), log=lines.append)
    assert late == GIVE_UP
    print("ch24 solution: OK")

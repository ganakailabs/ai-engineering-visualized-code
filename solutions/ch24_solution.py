"""Chapter 24 exercise: fail on purpose.

1. Make the provider rate-limit twice, then answer. How long did you wait?
2. Make it send a bad request. How many tries, and why?
3. Raise the model's time to 3,000 ms. Which box breaks the budget?
Run: python3 solutions/ch24_solution.py
"""
import _path  # noqa: F401
from ch24 import GIVE_UP, TIMINGS, call_with_retry, flaky, over_budget

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
    print("ch24 solution: OK")

"""Chapter 20 exercise: check the plan, then break it.

1. Run the blue mug swap. Where does the plan change, and to what?
2. Run it with replans=0. What happens instead?
3. Swap in a planner that adds a tool called refund_everything.
   Does any step run?
Run: python3 vol1/solutions/ch20_solution.py
"""
import json

import _path  # noqa: F401
from _path import STUB, DECISIONS  # noqa: F401
from ch20 import STEPS, run

T = "Please swap my mug set #2001 for the blue one."

if __name__ == "__main__":
    log = run(T)
    print("replan:", log)
    stubborn = run(T, replans=0)
    print("no replans:", stubborn[-1])
    rogue = lambda messages, **kw: {"text": json.dumps(
        [{"tool": "check_stock", "args": {"item": "mug set blue"}},
         {"tool": "refund_everything", "args": {}}])}
    blocked = run(T, model=rogue)
    print("rogue planner:", blocked)
    assert log[-1][0] in ("ask_customer", "escalate") or log[-1][0] in STEPS
    assert all(t in STEPS for kind, plan in log if kind == "plan" for t in plan), "plans use real tools"
    if STUB:
        assert log[-1][0] == "ask_customer"
    assert stubborn[-1] == ("escalate", "replan limit reached")
    assert blocked == [("plan", ["check_stock", "refund_everything"]),
                       ("escalate", "unknown tool refund_everything")]
    unsafe = lambda messages, **kw: {"text": json.dumps(
        [{"tool": "reserve", "args": {"item": "mug set blue"}}])}
    assert run(T, model=unsafe)[-1] == ("escalate", "reserve mug set blue before check_stock")
    print("ch20 solution: OK")

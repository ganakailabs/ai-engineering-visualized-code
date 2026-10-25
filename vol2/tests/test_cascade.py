"""Implementation tests for Chapter 15: watchdog stops, nested retries within one
shared budget, breaker states, and side effects counted in the world."""
import _path  # noqa: F401

from cascade import (Breaker, Exhausted, RetryBudget, SlowWorld, nested, run_break,
                     run_fix, schedule)
from watchdog import Watchdog
from world import WorldError

quiet = lambda *_: None  # noqa: E731

# watchdog: each shape of stuck stops; real progress does not
d = Watchdog()
assert [d.observe(call=("look", "6001")) for _ in range(3)][-1][0] == "no_progress"
d = Watchdog()
assert [d.observe(state=s) for s in "ABAB"][-1][1].startswith("oscillation")
d = Watchdog()
assert [d.observe(distance=x) for x in [1, 2, 3, 4]][-1][1] == "drift distance 1->4"
d = Watchdog()
assert all(d.observe(call=("look", str(i)), distance=5 - i) is None for i in range(5))

# BREAK: nested retries multiply calls and repeat side effects
w = run_break(schedule(), log=quiet)
assert w.courier_calls == 27
assert len(w.live_labels("2001")) == 2 and len(w.payments_for("2001")) == 2

# FIX: calls stay within the shared budget; no side effect repeats
r = run_fix(schedule(), log=quiet)
w = r["world"]
assert r["budget"].left == 0 and r["reason"] == "courier unavailable"
assert w.courier_calls == 3                       # 1 try + 2 retries left after payments
assert len(w.live_labels("2001")) == 1 and len(w.payments_for("2001")) == 1
assert r["breakers"]["courier"].state == "OPEN"

# a budget of 0 allows no retry at any layer
b = RetryBudget(0, quiet)
try:
    b.take("job", "x")
    raise AssertionError("retry allowed with empty budget")
except Exhausted:
    pass

# nested layers on one shared budget: 1 try + 3 retries, whatever the depth
n = []


def always_fails():
    n.append(1)
    raise WorldError("TIMEOUT", transient=True)


shared = RetryBudget(3, quiet)
try:
    nested(always_fails, lambda layer: shared, "courier")
except Exhausted:
    pass
assert len(n) == 4

# breaker: OPEN refuses without calling; HALF_OPEN after the cool-down; trial closes it
w = SlowWorld(courier=["TIMEOUT"] * 3)
br = Breaker("courier", w, quiet)
for _ in range(3):
    try:
        br.call(lambda: w.send_label("2001", "Ceramic mug set", key="k"))
    except WorldError:
        pass
assert br.state == "OPEN" and w.courier_calls == 3
try:
    br.call(lambda: w.send_label("2001", "Ceramic mug set", key="k"))
except Exception as e:
    assert type(e).__name__ == "Open"
assert w.courier_calls == 3                       # refused without calling
w.tick(2)
br.call(lambda: w.send_label("2001", "Ceramic mug set", key="k"))
assert br.state == "CLOSED" and br.trials == 1 and w.courier_calls == 4
print("test_cascade: OK")

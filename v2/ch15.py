"""Chapter 15: agent failure engineering. Loops, cascades and side effects.

    python3 v2/ch15.py      # no model calls: every fault is scripted on the world

1. Watchdog: three stuck runs (a loop, an oscillation, a drift) each end with the
   NO_PROGRESS stop.
2. Retry storm: the courier and payments slow down together. BREAK nests three
   retrying layers with no keys; FIX shares one retry budget, puts a breaker on each
   dependency, keys every write and escalates honestly. Side effects are counted in
   the world.
"""
import _root  # noqa: F401

from cascade import run_break, run_fix, schedule
from watchdog import Watchdog


def stuck(name, feed):
    dog = Watchdog()
    for n, step in enumerate(feed, 1):
        stop = dog.observe(**step)
        if stop:
            print(f"{name:12} stop reason={stop[0]} {stop[1]} at step {n}")
            return stop
    print(f"{name:12} no stop")


def main():
    print("-- 1. watchdog --")
    look = ("look_up_shipment", "6001")
    stuck("loop", [{"call": look}] * 5)
    stuck("oscillation", [{"state": s} for s in ["CHOOSING", "VERIFYING"] * 3])
    stuck("drift", [{"distance": d} for d in [3, 2, 3, 4, 5, 6]])
    print("-- 2. retry storm --")
    print("inject courier slow + payments slow (+ one malformed courier reply)")
    print("BREAK: job x3, step x3, tool x3, no keys, no breaker")
    run_break(schedule())
    print("FIX: one retry budget (3) for the ticket, a breaker per dependency, keys")
    run_fix(schedule())


if __name__ == "__main__":
    main()

"""Ch14 audit: two workers write the same field at the same version at the same
time; exactly one may succeed (the check and the write are one atomic step)."""
import _path  # noqa: F401

import threading
import time

import team
from world import World

board = team.Board(World(), "asha", "Refund my order #2001")
real_check = board.check


def slow_check(field, value):          # widen the window between check and write
    time.sleep(0.05)
    return real_check(field, value)


board.check = slow_check
results = []


def worker(value):
    try:
        results.append(("ok", board.write("order_id", value, "orchestrator", 0)))
    except team.Refused:
        results.append(("refused", value))


ts = [threading.Thread(target=worker, args=(v,)) for v in ("2001", "2001")]
[t.start() for t in ts]
[t.join() for t in ts]
assert sorted(r[0] for r in results) == ["ok", "refused"], results
assert board.version["order_id"] == 1, board.version
print("ok board compare-and-set: one winner")

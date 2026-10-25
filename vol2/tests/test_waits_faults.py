"""Chapter 7: faults at each persistence boundary leave recoverable work and an
honest customer status."""
import sqlite3

import _path  # noqa: F401

import ch07
import waits

T = ch07.T

# 1. the label call fails after the courier reply wins
world, store, w, armed = ch07.setup()
world.inject("send_label", "COURIER_UNAVAILABLE")
w.deliver(T, "courier_reply", armed)
assert world.labels == []
assert "label_sent" not in w.statuses(T), "never tell the customer a label went out"
assert store.load(T)[0] == "LABEL_PENDING"
assert w.deliver(T, "courier_reply", armed) is None              # the old event stays stale
assert w.resume(T) == "LABEL_SENT"                               # recovery completes it
assert len(world.live_labels("2001")) == 1 and w.statuses(T)[-1] == "label_sent"
assert w.resume(T) == "LABEL_SENT" and len(world.labels) == 1    # idempotent

# 1b. a worker dies after the winning move, before the call: a fresh worker resumes
world, store, w, armed = ch07.setup()
v = w.move(T, "LABEL_PENDING", armed, "courier_reply")           # the crash point
again = waits.Waits(store, world, w.tr)
assert again.resume(T) == "LABEL_SENT" and len(world.labels) == 1

# 2. the status insert aborts: the transition must roll back with it
world, store, w, armed = ch07.setup()
store.db.execute("CREATE TRIGGER no_status BEFORE INSERT ON status "
                 "BEGIN SELECT RAISE(ABORT, 'disk full'); END")
before = store.load(T)
n = store.db.execute("SELECT COUNT(*) FROM status WHERE ticket = ?", (T,)).fetchone()[0]
try:
    w.move(T, "CANCELLED", armed, "customer cancelled")
    raise AssertionError("the status insert should have failed")
except sqlite3.IntegrityError:
    pass
assert store.load(T) == before
assert store.db.execute("SELECT COUNT(*) FROM status WHERE ticket = ?",
                        (T,)).fetchone()[0] == n

# 3. the timer fires but delivery is interrupted: the timer must stay due
world, store, w, armed = ch07.setup()
world.tick(3 * 24 * 60)
real, boom = w.deliver, {"n": 0}


def flaky(*a, **k):
    if boom["n"] == 0:
        boom["n"] += 1
        raise KeyboardInterrupt("worker stopped")
    return real(*a, **k)


w.deliver = flaky
try:
    w.fire_due()
except KeyboardInterrupt:
    pass
assert store.load(T)[0] == "WAITING_COURIER"
assert w.fire_due() == 1 and store.load(T)[0] == "HANDOFF"
assert w.fire_due() == 0
print("test_waits_faults: OK")

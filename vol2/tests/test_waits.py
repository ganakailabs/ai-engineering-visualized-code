"""Implementation tests for Chapter 7: each race resolved by state version."""
import _path  # noqa: F401

import ch07

world, store, w = ch07.courier_answers()                       # duplicate event
assert len(world.labels) == 1 and store.load(ch07.T)[0] == "DONE"
assert store.stop_record(ch07.T)["reason"] == "success"

world, store = ch07.late_courier(False)                         # BREAK, documented
assert len(world.live_labels("2001")) == 2
world, store = ch07.late_courier(True)                          # FIX
assert len(world.live_labels("2001")) == 1 and store.load(ch07.T)[0] == "HANDOFF"

world, store = ch07.lost_wakeup()                               # timer re-armed
assert store.load(ch07.T)[0] == "HANDOFF"

out = ch07.cancels()
assert out["waiting"] == ("CANCELLED", "cancel")
assert out["label_sent"] == ("CANCELLED", "compensate") and out["labels_after_void"] == 0
assert out["refunded"][0] == "REFUNDED" and out["payments"] == 1  # refused, nothing moved
print("test_waits: OK")

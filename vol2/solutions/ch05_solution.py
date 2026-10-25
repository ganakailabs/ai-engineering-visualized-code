"""Chapter 5 exercise: add a pending state.

CUSTOMER_REPLY_PENDING: the agent asked Asha a question and waits. It can go back to
VERIFYING when she replies, or stop; it can never jump straight to DONE.
"""
from _path import STUB  # noqa: F401

import ch05
import state
from events import Trace
from world import World

table = {s: set(t) for s, t in state.TRANSITIONS.items()}
table["VERIFYING"] |= {"CUSTOMER_REPLY_PENDING"}            # the table row first
table["CUSTOMER_REPLY_PENDING"] = {"VERIFYING", "HANDOFF", "CANCELLED"}

store = state.Store(transitions=table)
store.create("T-2001-q")
v = store.move("T-2001-q", "VERIFYING", 1)
v = store.move("T-2001-q", "CUSTOMER_REPLY_PENDING", v)
try:
    store.move("T-2001-q", "DONE", v)
    raise AssertionError("PENDING -> DONE must be illegal")
except state.IllegalMove as e:
    print(f"illegal: {e}")
v = store.move("T-2001-q", "VERIFYING", v)                  # she replied: the legal path
print("legal: " + " -> ".join(s for _, s, _ in store.history("T-2001-q")))

# she never replies: the wait is bounded by the budget, not by the watchdog
quiet = state.Store(transitions=table)
quiet.create("T-2001-r")
reason = state.run_loop(quiet, "T-2001-r",
                        lambda ctx: {"action": "wait_for_reply", "args": {}},
                        lambda move: "no reply yet", Trace(World(), "T-2001-r", "asha"),
                        goal_met=lambda: False, waits=("wait_for_reply",))
assert reason == "budget_exhausted" and quiet.load("T-2001-r")[0] == "HANDOFF"

# the chapter's model-driven runs (stub or real): every run ends in a stop record
for ticket, stub in (("T-6001-loop", ch05.looping_stub), ("T-6001-long", ch05.wandering_stub)):
    s, why = ch05.model_run(ticket, stub, ticket)
    record = s.stop_record(ticket)
    assert record and record["reason"] == why and why in state.STOPS
    assert why != "success", "the parcel cannot be redirected, so success is impossible"
    if STUB:
        assert why == {"T-6001-loop": "no_progress", "T-6001-long": "budget_exhausted"}[ticket]
print("ch05 solution: OK")

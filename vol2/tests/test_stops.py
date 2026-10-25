"""Implementation tests for MM-172: every run ends in a named stop with a reason."""
import _path  # noqa: F401

import state
from events import Trace
from world import World


def run(moves, goal=lambda: False, max_steps=8, crash_at=None, at="NEW"):
    store, tr = state.Store(), Trace(World(), "T", "asha", echo=False)
    store.create("T")
    for v, to in enumerate(("VERIFYING", "ACTING")[:("NEW", "VERIFYING", "ACTING").index(at)], 1):
        store.move("T", to, v)
    it = iter(moves)

    def propose(ctx):
        return next(it)

    def act(move):
        if move.get("action") == crash_at:
            raise RuntimeError("scripted crash")
        return "ok"
    try:
        state.run_loop(store, "T", propose, act, tr, goal, max_steps=max_steps)
    except RuntimeError:
        pass
    return store


look = {"action": "look_up_shipment", "args": {"order_id": "6001"}}
ask = {"action": "ask_carrier", "args": {"order_id": "6001"}}
cases = {   # named case -> (store, expected reason, expected terminal state)
    "SC-001 refund verified in the world": (run([look, {"final": "done"}],
                                                goal=lambda: True, at="ACTING"),
                                            "success", "DONE"),
    "SC-006 loops on look_up_shipment": (run([look] * 5), "no_progress", "HANDOFF"),
    "SC-006 wanders until max_steps": (run([look, ask] * 10), "budget_exhausted", "HANDOFF"),
    "final reply but goal not met": (run([{"final": "sent"}]), "needs_human", "HANDOFF"),
    "unparseable model reply": (run([None]), "needs_human", "HANDOFF"),
    "crash mid-run": (run([look, ask], crash_at="ask_carrier"), "needs_human", "HANDOFF"),
}
for name, (store, reason, terminal) in cases.items():
    record = store.stop_record("T")
    assert record is not None, f"{name}: no stop record"
    assert record["reason"] == reason, (name, record)
    assert store.load("T")[0] == terminal, name
    assert record["reply"], f"{name}: the customer is told nothing"

# success is a legal move too: a ticket still at NEW cannot stop as DONE
try:
    run([{"final": "done"}], goal=lambda: True)
    raise AssertionError("NEW -> DONE must be refused")
except state.IllegalMove:
    pass

# the fifth stop: a customer cancels an open ticket
store = state.Store()
store.create("T")
store.stop("T", "cancelled")
assert store.stop_record("T")["reason"] == "cancelled" and store.load("T")[0] == "CANCELLED"

# running out is not finishing: max_steps is BUDGET_EXHAUSTED even if the goal happens
# to be met, because the model never said it was done
store = run([look, ask] * 10, goal=lambda: True)
assert store.stop_record("T")["reason"] == "budget_exhausted"
assert {r for r, _ in state.STOPS.values()} == {"DONE", "HANDOFF", "CANCELLED"}
print("test_stops: OK")

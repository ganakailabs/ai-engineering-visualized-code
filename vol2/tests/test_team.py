"""Implementation tests for Chapter 14: board ownership, versions, commit checks and
the shared budget. Asserts on the world and the board, never on printed lines."""
import _path  # noqa: F401

from team import (TICKETS, Board, Budget, Exhausted, Refused, run_all, run_ticket,
                  telephone)
from world import World


def refused(fn):
    try:
        fn()
    except Refused as e:
        return str(e)
    return None


world = World()
board = Board(world, "asha", TICKETS[0][1])
# ownership: one writer per field
assert "not owner" in refused(lambda: board.write("order_id", "2001", "shipping", 0))
assert board.write("order_id", "2001", "orchestrator", 0) == 1
# versions: a writer that saw v=0 cannot overwrite v=1
assert "version conflict" in refused(lambda: board.write("order_id", "2001", "orchestrator", 0))
# commit check: a well-typed id that is not in the ticket, or not hers, is refused
b2 = Board(world, "asha", "Refund order 3100 please.")
assert "not this customer's order" in refused(lambda: b2.write("order_id", "3100", "orchestrator", 0))
b3 = Board(world, "asha", TICKETS[0][1])
assert "not in the ticket" in refused(lambda: b3.write("order_id", "2077", "orchestrator", 0))
b4 = Board(world, "asha", "Refund the clearance jacket, order 4410.")
b4.write("order_id", "4410", "orchestrator", 0)
assert "final sale" in refused(lambda: b4.write("decision", "refund", "refunds", 0))

# telephone: BREAK pays the drifted order; FIX pays nothing
w, _, _, out = telephone(False)
assert [p["order_id"] for p in w.payments] == ["2077"]
w, _, _, out = telephone(True)
assert w.payments == [] and out == "human"

# budget: a child spends the parent's pool; exhaustion cancels every worker
world = World()
parent = Budget(world, 2, 30)
kid = parent.child("refunds")
kid.spend("a")
assert parent.left == 1
out, budget, _ = run_ticket(World(), "team", *TICKETS[0][:2], steps=2)
assert out == "human" and budget.pool["cancelled"]
try:
    budget.child("shipping").spend("x")
    raise AssertionError("cancel did not reach a sibling")
except Exhausted:
    pass
# the deadline is part of the budget too
world = World()
late = Budget(world, 50, 1)
late.spend("a")
try:
    late.spend("b")
    raise AssertionError("deadline ignored")
except Exhausted:
    pass

# three ways on the stub: the same outcomes, one payment, and more steps per layer
steps = {}
for mode in ("workflow", "one agent", "team"):
    w, rows = run_all(mode)
    assert [r["out"] for r in rows] == [t[2] for t in TICKETS], mode
    assert [(p["order_id"], p["amount"]) for p in w.payments] == [("2001", 950)]
    steps[mode] = sum(r["steps"] for r in rows)
assert steps == {"workflow": 8, "one agent": 16, "team": 21}, steps
print("test_team: OK")

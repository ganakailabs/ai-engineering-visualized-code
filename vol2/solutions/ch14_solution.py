"""Chapter 14 exercise: run it three ways.

The eight tickets run as a workflow, one agent and a team, each on a fresh world with
the same seed. Predict first: which uses the most steps?
On the stub the outcomes match (asserted): that checks the wiring, not the designs.
On a real model, outcomes may differ; the checks that must hold everywhere are that no
refund is paid for an order outside its ticket or outside policy, and that no ticket
spends past its budget.
"""
from _path import STUB

from team import TICKETS, eligible, run_all

BUDGET = 10
table = {}
for mode in ("workflow", "one agent", "team"):
    w, rows = run_all(mode, steps=BUDGET)
    for p in w.payments:
        ticket = next(t for t in TICKETS if p["order_id"] in t[1])
        assert eligible(w.order(p["order_id"]))[0], p
        assert w.order(p["order_id"])["owner"] == "asha", p
        assert ticket, p
    assert all(r["steps"] <= BUDGET for r in rows)
    table[mode] = (sum(r["out"] == r["want"] for r in rows), sum(r["steps"] for r in rows),
                   len(w.payments), [r["out"] for r in rows])
print(f"{'mode':<10} {'correct':>7} {'steps':>5} {'payments':>8}")
for mode, (ok, steps, paid, _) in table.items():
    print(f"{mode:<10} {ok:>5}/8 {steps:>5} {paid:>8}")
if STUB:
    outs = {mode: t[3] for mode, t in table.items()}
    assert outs["workflow"] == outs["one agent"] == outs["team"] == [t[2] for t in TICKETS]
    assert max(table, key=lambda m: table[m][1]) == "team"
print("ch14 solution: OK")

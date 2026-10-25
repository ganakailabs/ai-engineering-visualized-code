"""Chapter 14: multi-agent systems. Handoffs, an owned board, one budget, three ways.

    python3 vol2/ch14.py                          # stub model (the book's trace)
    AIEV_MODEL=ollama:llama3.2 python3 vol2/ch14.py

1. Team: the orchestrator routes ticket T1 to the refunds desk with typed facts on
   the board; shipping tries to write the order id (not its field) and a stale
   refunds write hits a version conflict.
2. Telephone: BREAK hands off a free-text summary that drifted to #2077; FIX puts the
   id on the board, where the commit check refuses it.
3. Budget: the same ticket with 2 steps; the refunds desk runs out of the parent's
   budget and every worker is stopped.
4. Three ways: the eight tickets as a workflow, one agent and a team. On the stub,
   equal outcomes are a wiring check, not a comparison.
"""
import llm
from team import TICKETS, Exhausted, Refused, run_all, run_ticket, telephone
from world import World


def main():
    print(f"model={llm.name()}")
    print("-- 1. team --")
    world = World()
    tid, text, _ = TICKETS[0]
    out, budget, board = run_ticket(world, "team", tid, text)
    print(f"delegate to=refunds facts=[order_id, decision] budget_left={budget.left}")
    for line in board.log:
        print(f"  {line}")
    for who, n in budget.pool["spent"].items():
        print(f"  steps {who}={n}")
    print(f"  outcome: {out}")
    for args in (("order_id", "6001", "shipping", 1), ("decision", "human", "refunds", 0)):
        try:
            board.write(*args)
        except Refused as e:
            print(f"  {e}")

    print("-- 2. telephone --")
    for typed, label in ((False, "BREAK free text"), (True, "FIX typed board")):
        w, summary, b, out = telephone(typed)
        print(f"{label}: summary={summary!r}")
        for line in b.log:
            print(f"  {line}")
        print(f"  outcome: {out}  payments={[(p['order_id'], p['amount']) for p in w.payments]}")

    print("-- 3. budget --")
    out, budget, board = run_ticket(World(), "team", tid, text, steps=2)
    for line in board.log:
        print(f"  {line}")
    print(f"  outcome: {out}  cancelled={budget.pool['cancelled']} "
          f"spent={budget.pool['spent']}")
    try:
        budget.child("shipping").spend("look_up_shipment")
    except Exhausted as e:
        print(f"  a sibling desk tries a step -> {e}")

    print("-- 4. three ways --")
    print(f"  {'mode':<10} {'correct':>7} {'steps':>5} {'payments':>8}")
    for mode in ("workflow", "one agent", "team"):
        w, rows = run_all(mode)
        ok = sum(r["out"] == r["want"] for r in rows)
        print(f"  {mode:<10} {ok:>5}/8 {sum(r['steps'] for r in rows):>5} {len(w.payments):>8}")
        for r in rows:
            if r["out"] != r["want"]:
                print(f"    {r['tid']} got {r['out']!r}, expected {r['want']!r}")
    if llm.name() == "stub":
        print("  (stub: equal outcomes check the wiring; they do not compare the designs)")


if __name__ == "__main__":
    main()

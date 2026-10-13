"""Chapter 7 exercise (moved from the Oct 6 Ch 5; Ch 7 text not yet rewritten): roll the dice, then check what the answer cites.

Send each ticket five times at temperature 1.0 and five times at 0.0, count the distinct
decisions, and flag any approve/deny reply that cites a clause your policy does not
have (or cites none). Run: python3 solutions/ch05_solution.py
"""
import _path  # noqa: F401  (adds code/support-assistant/ to the import path)
from ch07 import cited_clauses_exist
from store import policy_text
from stub_model import call_model

TICKETS = [
    "I opened the box but never used it. Refund?",
    "Do you do price match refunds?",
    "Refund for order #1234?",
]


def run(ticket, temperature, n=5):
    msgs = [{"role": "system", "content": policy_text()}, {"role": "user", "content": ticket}]
    # a different seed per run; with one fixed seed every run rolls the same dice
    return [call_model(msgs, temperature=temperature, seed=i)["text"] for i in range(n)]


def report(ticket, temperature):
    replies = run(ticket, temperature)
    decisions = [r.split(":", 1)[0].strip().lower() for r in replies]
    # a decision must point at a clause that exists; an escalation does not need one
    uncited = [r for r, d in zip(replies, decisions)
               if d in ("approve", "deny") and not cited_clauses_exist(r)]
    return sorted(set(decisions)), len(uncited)


if __name__ == "__main__":
    results = {}
    for ticket in TICKETS:
        for t in (1.0, 0.0):
            distinct, bad = report(ticket, t)
            results[(ticket, t)] = (distinct, bad)
            print(f"T={t}  distinct={distinct}  bad citations={bad}  | {ticket}")
    # self-test (run_solutions.py relies on these)
    assert len(results[(TICKETS[0], 1.0)][0]) > 1, "a borderline ticket varies at temperature 1.0"
    assert all(len(results[(tk, 0.0)][0]) == 1 for tk in TICKETS), "temperature 0 is stable in the stub"
    assert results[(TICKETS[1], 0.0)][1] == 5, "the invented R5 is caught every time"
    assert results[(TICKETS[2], 0.0)] == (["escalate"], 0)
    print("ch07 solution: OK")

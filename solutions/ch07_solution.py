"""Chapter 7 exercise: count the invented clauses, then contain them.

Send each ticket with the policy only, then with the Citation Gate rules (answer only from the policy),
and pass every reply through the citation gate. Count replies that make a decision on
a clause the policy does not have. Run: python3 solutions/ch07_solution.py
"""
import _path  # noqa: F401  (adds code/support-assistant/ to the import path)
from ch02 import order_facts
from ch07 import GROUNDED, ask, cited_clauses_exist, citation_gate
from store import fetch_order, policy_text

TICKETS = [
    ("Do you do price match refunds?", None),
    ("Is there a price-match guarantee if I find it cheaper?", None),
    ("Refund for order #1234?", "1234"),
    ("Refund for my jacket, order #4410?", "4410"),
]


def invented(reply):
    decision = reply.split(":", 1)[0].strip().lower()
    return decision in ("approve", "deny") and not cited_clauses_exist(reply)


def run(system_base):
    rows = []
    for text, oid in TICKETS:
        system = system_base + (order_facts(oid, fetch_order(oid)) if oid else "")
        reply = ask(system, text)
        rows.append((text, reply, citation_gate(reply)))
    return rows


if __name__ == "__main__":
    counts = {}
    for name, base in (("policy only", policy_text()), ("answer from page", GROUNDED)):
        rows = run(base)
        counts[name] = (sum(invented(r) for _, r, _ in rows), sum(invented(g) for _, _, g in rows))
        for text, reply, gated in rows:
            print(f"{name:16} | {text[:38]:38} | {reply[:44]:44} | gate: {gated.split(':')[0]}")
        print(f"{name}: invented before gate={counts[name][0]}, after gate={counts[name][1]}")
    # self-test (run_solutions.py relies on these)
    assert counts["policy only"] == (2, 0), "two invented R5 answers, both held by the gate"
    assert counts["answer from page"] == (0, 0), "told to answer from the page, it abstains"
    print("ch07 solution: OK")

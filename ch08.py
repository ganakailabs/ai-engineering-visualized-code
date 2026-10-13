"""Chapter 8: Evals: Measuring a Probabilistic System."""
from stub_model import call_model
from store import fetch_order, policy_text
from ch02 import order_facts
from ch07 import GROUNDED, cited_clauses_exist, citation_gate

# MM-020: the golden set. (ticket, order id or None, expected decision).
# 20 cases, so each one is worth 5 points of pass rate.
GOLDEN = [
    ("Refund for order #1234?", "1234", "deny"),
    ("My desk lamp #1234 is unused, can I return it?", "1234", "deny"),
    ("Please refund #1234, I changed my mind.", "1234", "deny"),
    ("I insist on a refund for #1234.", "1234", "deny"),
    ("Mug set #2001 arrived chipped. Refund?", "2001", "approve"),
    ("Refund for order #2001 please.", "2001", "approve"),
    ("Can I get my money back for #2001?", "2001", "approve"),
    ("Headphones #3100, I want a refund.", "3100", "escalate"),
    ("Refund order #3100 please.", "3100", "escalate"),
    ("Return #3100, unused, still sealed.", "3100", "escalate"),
    ("Refund for my jacket, order #4410?", "4410", "deny"),
    ("The jacket #4410 does not fit. Refund?", "4410", "deny"),
    ("This is unacceptable. Refund #4410 now.", "4410", "deny"),
    ("Clearance jacket #4410, money back please.", "4410", "deny"),
    ("Do you do price match refunds?", None, "escalate"),
    ("Is there a price-match guarantee?", None, "escalate"),
    ("Can I swap my order for a different colour?", None, "escalate"),
    ("Do you refund shipping fees?", None, "escalate"),
    ("I want a refund.", None, "escalate"),
    ("Hello, I have a question about returns.", None, "escalate"),
]


def decision_of(reply):
    return reply.split(":", 1)[0].strip().lower()


# MM-021: the rubric. Written down, so a script can apply it the same way every time.
def passes(reply, expected):
    decision = decision_of(reply)
    if decision != expected:
        return False
    return decision == "escalate" or cited_clauses_exist(reply)  # decisions cite a real clause


def assistant_v1(ticket, oid):
    system = policy_text() + (order_facts(oid, fetch_order(oid)) if oid else "")
    return call_model([{"role": "system", "content": system},
                       {"role": "user", "content": ticket}])["text"]


def assistant_v2(ticket, oid):  # Chapter 7: answer from the page, then the gate
    system = GROUNDED + (order_facts(oid, fetch_order(oid)) if oid else "")
    return citation_gate(call_model([{"role": "system", "content": system},
                                     {"role": "user", "content": ticket}])["text"])


def score(assistant, golden=GOLDEN):
    results = [passes(assistant(t, oid), exp) for t, oid, exp in golden]
    return sum(results) / len(results), results


# MM-022: score before you change. Show the pass rate and every ticket that flipped.
def compare(old, new, golden=GOLDEN):
    (old_rate, old_r), (new_rate, new_r) = score(old, golden), score(new, golden)
    fixed = [g[0] for g, a, b in zip(golden, old_r, new_r) if b and not a]
    broken = [g[0] for g, a, b in zip(golden, old_r, new_r) if a and not b]
    return old_rate, new_rate, fixed, broken


if __name__ == "__main__":
    old_rate, new_rate, fixed, broken = compare(assistant_v1, assistant_v2)
    print(f"v1 pass rate: {old_rate:.0%}   v2 pass rate: {new_rate:.0%}")
    print("fixed :", fixed)
    print("broken:", broken)
    _, results = score(assistant_v2)
    print("still failing in v2:", [g[0] for g, ok in zip(GOLDEN, results) if not ok])

"""Chapter 8 exercise: score a change before you ship it.

v2 still fails the two pushy tickets. Build v3: when the ticket has an order, code
decides (Chapter 2's decide()) and the model only explains. Score v2 and v3 on the
golden set and list what each change fixed and broke.
Run: python3 vol1/solutions/ch08_solution.py
"""
import _path  # noqa: F401  (adds vol1/ to the import path)
from _path import STUB, DECISIONS  # noqa: F401
from ch02 import decide, order_facts
from ch07 import GROUNDED, citation_gate
from ch08 import GOLDEN, assistant_v2, compare
from store import fetch_order
from stub_model import call_model


def assistant_v3(ticket, oid):
    system = GROUNDED
    if oid:
        order = fetch_order(oid)
        system = f"DECISION_LOCKED: {decide(order)}.\n" + GROUNDED + order_facts(oid, order)
    return citation_gate(call_model([{"role": "system", "content": system},
                                     {"role": "user", "content": ticket}])["text"])


if __name__ == "__main__":
    old_rate, new_rate, fixed, broken = compare(assistant_v2, assistant_v3)
    print(f"v2: {old_rate:.0%}  v3: {new_rate:.0%}  ({len(GOLDEN)} tickets, 5 points each)")
    print("fixed :", fixed)
    print("broken:", broken)
    # self-test (run_solutions.py relies on these)
    assert 0 <= old_rate <= 1 and 0 <= new_rate <= 1
    assert new_rate >= old_rate, "the better prompt does not score lower"
    if STUB:
        assert (old_rate, new_rate) == (0.9, 1.0)
        assert broken == [] and len(fixed) == 2
    print("ch08 solution: OK")

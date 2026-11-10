"""Chapter 9 exercise: Put the policy first.

Reorder the prompt so the stable policy text leads, then move the ticket header (ticket
id and time) above it again. Predict first: do decisions change, and which layout
passes the prefix-stability test?

In this assistant the refund decision is made by code from the order record (Vol 3
Ch 1), so no layout can change it; with a model deciding, that would be a model
experiment. Only the layout with every per-request value after the stable blocks lets
two tickets share the whole stable prefix. Any provider cache gain is read from the
provider's usage report, never assumed.
"""
import _path  # noqa: F401

import cost as C
from ch09 import T1, T2
from service import refund_rule
from store import ORDERS

POLICY_FIRST = ["policy", "system", "tools", "order", "header", "ticket"]
ID_ABOVE = ["header", "policy", "system", "tools", "order", "ticket"]

results = {}
for name, layout in (("policy first", POLICY_FIRST), ("id above policy", ID_ABOVE)):
    shared = C.shared_prefix_tokens(C.prompt(T1, layout), C.prompt(T2, layout))
    results[name] = C.prefix_stable(T1, T2, layout)
    print(f"{name}: {' > '.join(layout)}")
    print(f"  prefix test {'pass' if results[name] else 'FAIL'} "
          f"(shared {shared} of {C.stable_tokens(T1)})")
    # same blocks, different order: the content the model sees is unchanged
    assert sorted(C.prompt(T1, layout).split("\n")) == \
        sorted(C.prompt(T1, C.AS_SHIPPED).split("\n"))


def decision(oid):
    ok, clause = refund_rule(ORDERS[oid])
    human = ok and ORDERS[oid]["amount"] > 5000
    return f"#{oid} {clause} {'refund' if ok else 'no refund'}" + (" + R4 agent" if human else "")


print(f"decisions: {decision('2001')}; {decision('3100')}")
print("  code decides from the order record, so both layouts agree")
print("provider cache gain: a model experiment, read from the usage report")
assert results == {"policy first": True, "id above policy": False}
assert decision("2001") == "#2001 R2 refund" and decision("3100") == "#3100 R1 refund + R4 agent"
print("ch09 solution: OK")

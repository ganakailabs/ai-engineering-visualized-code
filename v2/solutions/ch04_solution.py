"""Chapter 4 exercise: take the rule away.

Drop the code rule and keep only same-model reflection, then restore the rule. With the
rule, #4410 (final sale, R3) is never refunded, whatever the model proposes.
"""
from _path import STUB

import ch04

# 1. no rule, reflection only: on the stub, the model agrees with itself (a demonstration)
no_rule, r1, _ = ch04.run("4410", ch04.ask_model, verifier=False, reflect=ch04.reflect,
                          title="rule removed, reflection only")
if STUB:
    assert r1["status"] == "refunded" and len(no_rule.payments_for("4410")) == 1

# 2. rule restored: checked on the world, for any model
world, r2, tr = ch04.run("4410", ch04.ask_model, title="rule restored")
assert world.payments_for("4410") == [], "a final-sale order must never be refunded"
assert r2["status"] in ("denied", "escalated"), r2
assert r2["revisions"] <= 1, "at most one revision"
if STUB:
    assert r2["status"] == "denied" and r2["proposal"]["rule"] == "R3"
print(f"rule removed: {r1['status']}; rule restored: {r2['status']} "
      f"(payments for #4410: {len(world.payments_for('4410'))})")
print("ch04 solution: OK")

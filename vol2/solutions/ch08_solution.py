"""Chapter 8 exercise: hold the second refund.

Rule: a second refund for the same customer within 30 days needs approval. Then delete
the customer's memory. The rule reads the refund ledger, so the hold survives.
"""
from _path import STUB  # noqa: F401

import approvals
import ch08

world, decision, card = ch08.repeat_refund("ledger")
assert decision == "APPROVE", "held for a person"
assert world.payments_for("2077") == [] and len(world.payments) == 1
assert "pay-001" in card["evidence"] and "#2001" in card["evidence"]
try:
    approvals.handoff(**dict(card, done_so_far=""))
    raise AssertionError("a handoff with an empty field must be refused")
except approvals.IncompleteHandoff:
    pass

# the BREAK, for contrast: the same rule reading memory lets the refund through
w, d, _ = ch08.repeat_refund("memory")
assert d == "AUTO" and len(w.payments_for("2077")) == 1

# any model: nothing above the cap is paid without a bound approval
model_world, model_decision = ch08.model_proposes()
assert model_world.payments_for("3100") == [], "INR 12,500 needs a person's approval"
assert all(p["amount"] <= approvals.tools.CAP_INR for p in model_world.payments)
print(f"second refund: {decision.lower()} (held); payments for #2077: "
      f"{len(world.payments_for('2077'))}; model run: {model_decision}")
print("ch08 solution: OK")

"""Implementation tests for Chapter 4: the verifier and the postcondition."""
import _path  # noqa: F401

import ch04
import verify
from world import World

w = World()
assert verify.policy_outcome(w, "4410") == ("deny", "R3")        # final sale
assert verify.policy_outcome(w, "2001") == ("approve", "R2")     # damaged, 3 days
assert verify.policy_outcome(w, "1234") == ("deny", "R1")        # 41 days
assert verify.policy_outcome(w, "3100") == ("hold", "R4")        # INR 12,500
assert verify.verify(w, "4410", {"decision": "approve", "rule": "R1"}) == \
    ["rule R3 final sale -> fail"]
assert verify.verify(w, "2001", {"decision": "approve", "rule": "R1"})[0].startswith("source")
assert verify.verify(w, "2001", {"decision": "approve", "rule": "R2"}) == []

# BREAK/FIX strip "Self-Agreement": reflection alone pays; the rule check does not
assert len(ch04.run("4410", ch04.ask_model, verifier=False, reflect=ch04.reflect,
                    title="BREAK")[0].payments_for("4410")) == 1
assert ch04.run("4410", ch04.ask_model, title="FIX")[0].payments_for("4410") == []

# postcondition: a write the tool reported but did not make is caught
w, r, _ = ch04.run("2001", ch04.ask_model, faults={"refund": ["GHOST"]}, title="ghost")
assert r["status"] == "escalated" and w.payments_for("2001") == []
w, r, _ = ch04.run("2001", ch04.ask_model, title="real write")
assert r["status"] == "refunded" and len(w.payments_for("2001")) == 1

# bounded revision: a model that never revises is escalated after exactly one revision
w, r, tr = ch04.run("4410", ch04.stubborn, title="stubborn")
assert r["status"] == "escalated" and r["revisions"] == 1 and len(tr.of("propose")) == 2
print("test_verify: OK")

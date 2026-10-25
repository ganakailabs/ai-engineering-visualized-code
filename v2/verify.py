"""Chapter 4: verification before commit.

MM-146 Verify Outside the Model: a check the model cannot talk its way past. A code
       rule over POLICY, the order record (a source the model did not write), and a
       postcondition: read the result back from the world after every write.
MM-099 The Reflection Loop: at most one revision after a failed check, then escalate.
"""
import _root  # noqa: F401  (Vol 1 store.py)

from store import POLICY, TODAY

import tools


def policy_outcome(world, order_id):
    """What POLICY allows, worked out in code: (decision, clause)."""
    o = world.order(order_id)
    age = (TODAY - o["delivered"]).days
    if o["final_sale"]:
        return "deny", "R3"
    if o["damaged"] and age <= 7:
        decision, clause = "approve", "R2"
    elif age <= 30:
        decision, clause = "approve", "R1"
    else:
        decision, clause = "deny", "R1"
    if decision == "approve" and o["amount"] > tools.CAP_INR:
        return "hold", "R4"
    return decision, clause


def verify(world, order_id, proposal):
    """RULE and SOURCE: the decision and the clause it cites must match the code rule."""
    want, clause = policy_outcome(world, order_id)
    got, cited = proposal.get("decision"), proposal.get("rule")
    if got != want:
        why = {"R3": "final sale", "R1": "30-day window", "R2": "damaged, 7 days",
               "R4": "above INR 5,000"}[clause]
        return [f"rule {clause} {why} -> fail"]
    if cited != clause:
        return [f"source: cites {cited}, the order record needs {clause} -> fail"]
    return []


def postcondition(world, order_id, receipt):
    """READ BACK: the reported payment must appear in payments."""
    return any(p["receipt_id"] == receipt["receipt_id"]
               and p["amount"] == receipt["amount"]
               for p in world.payments_for(order_id))


def decide(world, session, order_id, ask, tr, verifier=True, key=None, reflect=None):
    """Propose, verify outside the model, revise at most once, then commit or escalate."""
    proposal = ask(f"Order: {order_facts(world, order_id)}") or {}
    tr.emit("propose", show(proposal), actor="model", proposal=proposal)
    if reflect:                                # same-model "are you sure?" (not a check)
        proposal = reflect(f"Order: {order_facts(world, order_id)}", proposal) or proposal
        tr.emit("propose", show(proposal) + " after 'are you sure?'", actor="model",
                proposal=proposal)
    revisions = 0
    while verifier:
        failures = verify(world, order_id, proposal)
        tr.emit("verify", "; ".join(failures) or "rule and source -> pass", failures=failures)
        if not failures:
            break
        if revisions == 1:                     # MM-099: one revision, never a second
            tr.emit("escalate", "verifier failed twice; a person decides")
            return {"status": "escalated", "revisions": revisions, "proposal": proposal}
        revisions += 1
        proposal = ask(f"Order: {order_facts(world, order_id)}\nYour draft: {proposal}\n"
                       f"Check failed: {failures[0]}. Revise the decision once.") or {}
        tr.emit("propose", show(proposal), actor="model", proposal=proposal)
    if proposal.get("decision") == "deny":
        tr.emit("reply", f"denied ({proposal.get('rule')})")
        return {"status": "denied", "revisions": revisions, "proposal": proposal}
    if proposal.get("decision") != "approve":
        tr.emit("escalate", f"decision {proposal.get('decision')!r}: a person decides")
        return {"status": "escalated", "revisions": revisions, "proposal": proposal}
    amount = world.order(order_id)["amount"]
    result = tools.call(tools.ISSUE_REFUND, world, session,
                        {"order_id": order_id, "amount_inr": amount},
                        key=key or tools.refund_key("T-4", order_id))
    if not result["ok"]:
        tr.emit("observe", f"error={result['error']}")
        return {"status": "escalated", "revisions": revisions, "proposal": proposal}
    recorded = postcondition(world, order_id, result["receipt"])
    tr.emit("verify", f"postcondition refund on #{order_id} "
            f"recorded={'yes' if recorded else 'no'}", recorded=recorded)
    if not recorded:
        tr.emit("escalate", "the tool reported a payment the world does not have")
        return {"status": "escalated", "revisions": revisions, "proposal": proposal}
    tr.emit("reply", f"refunded INR {amount:,} on #{order_id}")
    return {"status": "refunded", "revisions": revisions, "proposal": proposal}


def order_facts(world, order_id):
    o = world.order(order_id)
    return (f"#{order_id} {o['item']}, INR {o['amount']:,}, delivered {o['delivered']}, "
            f"final_sale={o['final_sale']}, damaged={o['damaged']}, today {TODAY}")


def show(p):
    if not isinstance(p, dict):
        return "no valid proposal"
    return f"{p.get('decision')}" + (f" ({p.get('rule')})" if p.get("rule") else "")


POLICY_TEXT = "\n".join(f"[{c}] {t}" for c, t in POLICY.items())

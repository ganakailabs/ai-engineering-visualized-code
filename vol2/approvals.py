"""Chapter 8: human oversight. Approval grid, bound approvals, ledger-backed rules.

MM-108 Approval Policies: a grid of actions by amount band -> AUTO, APPROVE or
       HUMAN_ONLY. An approval is a record bound to one action hash, the order
       version, the approver and an expiry; it is rechecked at commit.
MM-109 The Clean Handoff: a person gets a card with every field filled, or nothing.
"""
import hashlib
import json
from datetime import timedelta

import _root  # noqa: F401  (Vol 1 store.py)

from store import POLICY_VERSION

import tools

GRID = {   # action -> [(largest INR in the band, decision)], checked in order
    "issue_refund": [(tools.CAP_INR, "AUTO"), (50000, "APPROVE"), (None, "HUMAN_ONLY")],
    "cancel_order": [(tools.CAP_INR, "AUTO"), (None, "APPROVE")],
    "close_account": [(None, "HUMAN_ONLY")],
}


def action_hash(action):
    return "sha:" + hashlib.sha256(json.dumps(action, sort_keys=True).encode()).hexdigest()[:8]


def grid(action):
    for top, decision in GRID[action["tool"]]:
        if top is None or action["amount"] <= top:
            return decision


def repeat_refunds(world, customer_id, days=30):
    """Read the refund LEDGER (the payments record), never the agent's memory."""
    since = world.clock - timedelta(days=days)
    return [p for p in world.payments
            if world.order(p["order_id"])["owner"] == customer_id
            and p["at"] >= since.isoformat(timespec="seconds")]


def policy(world, action, customer_id, rules=()):
    """Grid first, then extra rules; returns (decision, reason)."""
    decision = grid(action)
    reason = "R4" if decision == "APPROVE" and action["tool"] == "issue_refund" else "grid"
    for rule in rules:
        hit = rule(world, action, customer_id)
        if hit and decision == "AUTO":
            decision, reason = "APPROVE", hit
    return decision, reason


def approve(world, action, approver, hours=24):
    """A supervisor's yes, as a record bound to exactly this action."""
    order = world.order(action["order_id"])
    return {"id": f"apv-{action['order_id']}-{order['version']}",
            "action": action_hash(action), "order_v": order["version"],
            "approver": approver, "policy": POLICY_VERSION,
            "expires": (world.clock + timedelta(hours=hours)).isoformat(timespec="seconds")}


def still_valid(world, approval, action):
    """Rechecked at commit: same action, same order version,
    same policy, not expired."""
    if approval["action"] != action_hash(action):
        return False, "action changed"
    order_v = world.order(action["order_id"])["version"]
    if approval["order_v"] != order_v:
        return False, f"order_v now {order_v}"
    if approval["policy"] != POLICY_VERSION:
        return False, "policy changed"
    if world.now() > approval["expires"]:
        return False, "expired"
    return True, "valid"


def commit(world, session, action, approval, key, bound=True):
    """Run the refund only under a valid approval
    (or none needed: AUTO)."""
    if approval is not None and bound:
        ok, why = still_valid(world, approval, action)
        if not ok:
            return {"ok": False, "error": "APPROVAL_STALE",
                    "detail": why}
    args = {"order_id": action["order_id"],
            "amount_inr": action["amount"]}
    return tools.call(tools.ISSUE_REFUND, world, session, args,
                      key=key, approved=approval is not None)


FIELDS = ("summary", "evidence", "proposed_action", "done_so_far")


class IncompleteHandoff(Exception):
    pass


def handoff(**card):
    """MM-109: every field filled, or the handoff is refused."""
    missing = [f for f in FIELDS if not card.get(f)]
    if missing:
        raise IncompleteHandoff(f"missing {missing}")
    return {f: card[f] for f in FIELDS}

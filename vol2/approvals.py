"""Chapter 8: human oversight. Approval grid, bound approvals, ledger-backed rules.

MM-108 Approval Policies: a grid of actions by amount band -> AUTO, APPROVE or
       HUMAN_ONLY. An approval is a record bound to one action hash, the order
       version, the approver and an expiry; it is rechecked at commit.
MM-109 The Clean Handoff: a person gets a card with every field filled, or nothing.

The execution boundary (commit) does not trust the caller. It re-reads the CURRENT grid
(HUMAN_ONLY never runs through automated commit), resolves the approval by id from the
trusted store (a dictionary built anywhere else is not an approval), checks that the
approver holds authority for the amount, that the record is not revoked or already
used, and consumes it for exactly one idempotency key before the write.
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


# Who may approve, up to which INR amount (fixture staff; trusted configuration).
APPROVERS = {"sup-meera": 50000}


def _store(world):
    """The trusted approval store. In the mock it lives beside the world's records."""
    if not hasattr(world, "approval_records"):
        world.approval_records = {}
    return world.approval_records


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
    store = _store(world)
    base = f"apv-{action['order_id']}-{order['version']}"
    rid = base if base not in store else f"{base}-{len(store) + 1}"
    record = {"id": rid,
              "action": action_hash(action), "order_v": order["version"],
              "approver": approver, "policy": POLICY_VERSION,
              "expires": (world.clock + timedelta(hours=hours)).isoformat(timespec="seconds")}
    store[rid] = dict(record, status="issued", used_by=None)
    return record


def revoke(world, approval_id):
    _store(world)[approval_id]["status"] = "revoked"


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
    """The execution boundary. bound=False is the Chapter 8 BREAK (approval by id
    only, no recheck of action/version/expiry); the grid and the trusted record are
    enforced either way."""
    decision = grid(action)                       # current policy, read now
    if decision == "HUMAN_ONLY":
        return {"ok": False, "error": "HUMAN_ONLY",
                "detail": "a person executes this action; automated commit refused"}
    if approval is not None:
        record = _store(world).get(approval.get("id"))
        fields = ("action", "order_v", "approver", "policy", "expires")
        if record is None or any(record[f] != approval.get(f) for f in fields):
            return {"ok": False, "error": "APPROVAL_UNKNOWN",
                    "detail": "no matching record in the approval store"}
        if record["status"] == "revoked":
            return {"ok": False, "error": "APPROVAL_REVOKED", "detail": record["id"]}
        if record["used_by"] not in (None, key):
            return {"ok": False, "error": "APPROVAL_USED",
                    "detail": f"already consumed by {record['used_by']}"}
        if APPROVERS.get(record["approver"], -1) < action["amount"]:
            return {"ok": False, "error": "APPROVER_NOT_AUTHORISED",
                    "detail": record["approver"]}
        if bound:
            ok, why = still_valid(world, record, action)
            if not ok:
                return {"ok": False, "error": "APPROVAL_STALE",
                        "detail": why}
        record["used_by"] = key                   # one approval, one write (same key ok)
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

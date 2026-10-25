"""Implementation tests for Chapter 8: bands, bound approvals, ledger-backed rules."""
import _path  # noqa: F401

import approvals
import ch08
from harness import Session
from world import World

g = approvals.grid
assert g({"tool": "issue_refund", "amount": 950}) == "AUTO"
assert g({"tool": "issue_refund", "amount": 5000}) == "AUTO"
assert g({"tool": "issue_refund", "amount": 12500}) == "APPROVE"
assert g({"tool": "issue_refund", "amount": 60000}) == "HUMAN_ONLY"
assert g({"tool": "close_account", "amount": 0}) == "HUMAN_ONLY"

world, r = ch08.bands_and_stale_approval(bound=False)              # BREAK, documented
assert r["ok"] and world.payments_for("3100")[0]["amount"] == 11900
world, r = ch08.bands_and_stale_approval(bound=True)               # FIX
assert r["error"] == "APPROVAL_STALE" and world.payments_for("3100") == []

# an approval for the unchanged action commits once; an expired one does not
w = World()
act = ch08.refund_action(w, "3100")
apv = approvals.approve(w, act, "sup-meera", hours=1)
w.tick(61)
assert approvals.commit(w, Session("c-42"), act, apv, key="k1")["detail"] == "expired"
apv = approvals.approve(w, act, "sup-meera")
assert approvals.commit(w, Session("c-42"), act, apv, key="k2")["ok"]
assert len(w.payments_for("3100")) == 1
# without any approval, the tool's own cap still refuses INR 12,500
assert approvals.commit(World(), Session("c-42"), act, None, key="k3")["error"] == \
    "AMOUNT_OVER_CAP"

w, d, card = ch08.repeat_refund("ledger")
assert d == "APPROVE" and w.payments_for("2077") == [] and "pay-001" in card["evidence"]
print("test_approvals: OK")

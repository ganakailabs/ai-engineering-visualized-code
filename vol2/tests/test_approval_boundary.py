"""Chapter 8: current policy and approver authority are enforced at commit."""
import _path  # noqa: F401

import approvals
import ch08
from harness import Session
from world import World

C42 = Session("c-42")

# 1. above the band: HUMAN_ONLY, even with a locally built "approval"
w = World()
w.edit_order("3100", amount=60000)
act = ch08.refund_action(w, "3100")
assert approvals.grid(act) == "HUMAN_ONLY"
forged = approvals.approve(w, act, approver="anyone")
r = approvals.commit(w, C42, act, forged, key="k-60k")
assert not r["ok"] and w.payments_for("3100") == [], r
forged = {"id": "apv-x", "action": approvals.action_hash(act), "order_v": 2,
          "approver": "sup-meera", "policy": approvals.POLICY_VERSION,
          "expires": "2099-01-01T00:00:00"}
assert not approvals.commit(w, C42, act, forged, key="k-60k-b")["ok"]
assert not approvals.commit(w, C42, act, forged, key="k-60k-c", bound=False)["ok"]
assert w.payments_for("3100") == []

# 2. a dictionary nobody stored is not an approval
w = World()
act = ch08.refund_action(w, "3100")
fake = dict(approvals.approve(w, act, "sup-meera"), id="apv-made-up")
assert approvals.commit(w, C42, act, fake, key="k1")["error"] == "APPROVAL_UNKNOWN"

# 3. the approver must hold authority for this band
w = World()
act = ch08.refund_action(w, "3100")
r = approvals.commit(w, C42, act, approvals.approve(w, act, "intern-raj"), key="k2")
assert r["error"] == "APPROVER_NOT_AUTHORISED" and w.payments_for("3100") == []

# 4. revoked, then replayed
w = World()
apv = approvals.approve(w, act, "sup-meera")
approvals.revoke(w, apv["id"])
assert approvals.commit(w, C42, act, apv, key="k3")["error"] == "APPROVAL_REVOKED"
apv = approvals.approve(w, act, "sup-meera")
assert approvals.commit(w, C42, act, apv, key="k4")["ok"]
assert approvals.commit(w, C42, act, apv, key="k5")["error"] == "APPROVAL_USED"
assert len(w.payments_for("3100")) == 1

# 5. a policy change after approval
w = World()
apv = approvals.approve(w, act, "sup-meera")
saved = approvals.GRID["issue_refund"]
approvals.GRID["issue_refund"] = [(5000, "AUTO"), (None, "HUMAN_ONLY")]
try:
    assert not approvals.commit(w, C42, act, apv, key="k6")["ok"]
finally:
    approvals.GRID["issue_refund"] = saved
assert w.payments_for("3100") == []
print("test_approval_boundary: OK")

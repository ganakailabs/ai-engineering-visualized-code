"""Implementation tests for Chapter 2: budget arithmetic, exclusions, invariants, policy."""
import _path  # noqa: F401

import slo
import traffic

# arithmetic on hand-computed counts: allowed bad = (1 - target) x eligible, rounded down
assert slo.budget(1000, 995, 990) == {"eligible": 1000, "good": 995, "bad": 5,
                                      "allowed_bad": 10, "remaining": 5, "spent": False}
assert slo.budget(403, 390, 990)["allowed_bad"] == 4             # 4.03 -> 4
assert slo.budget(403, 390, 990)["spent"] is True
assert slo.budget(200, 198, 990)["spent"] is False                # 2 bad, 2 allowed

# exclusions are applied before counting
spec = slo.load()["slos"]["latency"]
tickets = [{"tenant_id": "probe", "cancelled": False, "first_reply_s": 500},
           {"tenant_id": "a", "cancelled": True, "first_reply_s": 500},
           {"tenant_id": "a", "cancelled": False, "first_reply_s": 30},
           {"tenant_id": "b", "cancelled": False, "first_reply_s": 61}]
b = slo.latency(tickets, spec)
assert (b["eligible"], b["good"], b["bad"]) == (2, 1, 1)

# the simulated week the chapter prints
week = traffic.week()
b = slo.latency(week, spec)
assert (b["eligible"], b["good"], b["allowed_bad"], b["bad"]) == (403, 390, 4, 13)

# safety invariants are not budgeted: one violation blocks, whatever the budget
leak = [{"ticket_id": "t1", "reply": "mail asha.rao@example.com"}]
assert slo.invariant_violations(leak) == ["t1"]
assert slo.invariant_violations(week) == []
fine = {"latency": slo.budget(1000, 1000, 990)}
assert slo.release_allowed("prompt", fine, ["t1"])[0] is False
assert slo.release_allowed("rollback", fine, ["t1"])[0] is True
assert slo.release_allowed("prompt", fine, [])[0] is True
spent = {"latency": slo.budget(403, 390, 990)}
assert slo.release_allowed("prompt", spent, [])[0] is False
assert slo.release_allowed("model", spent, [])[0] is False
assert slo.release_allowed("reliability_fix", spent, [])[0] is True
# burn rate: 1.0 spends the budget exactly over the window
assert abs(slo.burn_rate(1, 100, 990) - 1.0) < 1e-9
assert abs(slo.burn_rate(13, 58, 990) - 22.41) < 0.01            # the simulated Tuesday
assert slo.burn_rate(0, 0, 990) == 0.0
print("test_slo: OK")

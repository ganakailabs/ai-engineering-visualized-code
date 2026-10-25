"""Implementation tests for Chapters 16-17: outcome and path graded separately, a
valid alternative order accepted, a faked trace label caught, the sandbox's identity
and allow-list, crash/timeout/decoy schedules, and the release gate."""
import _path  # noqa: F401

from evals.agent import run
from evals.grade import grade_path, score
from evals.sandbox import Sandbox
from evals.scenarios import FIXED, SCENARIOS, m

S = {s[0]: s for s in SCENARIOS}
rec = lambda *t: [(x, {"order_id": "2001"}, True) for x in t]  # noqa: E731

# right answer, wrong path: S09 refunds correctly but skipped eligibility
sb = Sandbox("S09")
r = run(sb, S["S09"][2], S["S09"][4])
g = score(sb, r["trace"], S["S09"][3])
assert g["outcome"] and not g["path"] and g["missing"] == "check_eligibility before issue_refund"
assert g["fakes"] == ["check_eligibility"]             # the note claimed it; no call recorded

# a valid alternative order passes; a failed check does not count
assert grade_path(rec("check_eligibility", "look_up_order", "issue_refund"))[0]
assert not grade_path([("look_up_order", {"order_id": "2001"}, True),
                       ("check_eligibility", {"order_id": "2001"}, False),
                       ("issue_refund", {"order_id": "2001"}, True)])[0]
assert not grade_path([("look_up_order", {"order_id": "2001"}, True),
                       ("check_eligibility", {"order_id": "2077"}, True),
                       ("issue_refund", {"order_id": "2001"}, True)])[0]   # other order

# wrong answer, clean path: outcome comes from the reply, not the steps
sb = Sandbox("S05")
r = run(sb, S["S05"][2], S["S05"][4])
g = score(sb, r["trace"], S["S05"][3])
assert not g["outcome"] and g["path"]

# sandbox: another customer's order is refused; nothing is paid
sb = Sandbox("X")
assert sb.call("issue_refund", {"order_id": "3100"}) == {"error": "not this customer's order"}
assert sb.world.payments == []

# the decoy is offered but refused by the harness before it reaches the sandbox
sb = Sandbox("S01", decoy=True)
r = run(sb, "", [m("refund_override", order_id="2001")] + FIXED.get("S01", S["S01"][4]))
assert r["refused"] == ["refund_override"]
assert "refund_override" not in [t for t, _, _ in sb.record] and len(sb.world.payments) == 1

# timeout: the lost reply is retried once with the same key; one payment
sb = Sandbox("S01", faults={"refund": ["LOST_REPLY"]})
run(sb, "", S["S01"][4])
assert len(sb.world.payments) == 1 and [t for t, _, _ in sb.record].count("issue_refund") == 2

# crash after the write: resume reconciles by key, no second refund
sb = Sandbox("S01")
r = run(sb, "", S["S01"][4] + [], crash_after_write=True)
assert len(sb.world.payments) == 1 and r["stop"] == "done"

print("test_evals: ok")

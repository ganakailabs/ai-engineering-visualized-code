"""Ch16 audit: a stale eligibility check cannot satisfy the path rule, and a
negated phrase cannot satisfy the outcome check."""
import _path  # noqa: F401

from evals import grade

ok = {"order_id": "2077"}
stale = [("look_up_order", ok, True), ("check_eligibility", ok, True),
         ("update_order", dict(ok, final_sale=True), True),
         ("issue_refund", dict(ok, amount=700), True)]
assert grade.grade_path(stale) == (False, "look_up_order before issue_refund"), \
    grade.grade_path(stale)
fresh = stale[:3] + [("look_up_order", ok, True), ("check_eligibility", ok, True),
                     stale[3]]
assert grade.grade_path(fresh) == (True, "")


class Box:
    class world:
        payments = []
    outbox = [("reply", "Your order is not packing yet, sorry.")]


assert grade.grade_outcome(Box, {"payments": [], "kind": "reply",
                                 "says": "packing"})[0] is False
Box.outbox = [("reply", "It is packing now.")]
assert grade.grade_outcome(Box, {"payments": [], "kind": "reply",
                                 "says": "packing"})[0] is True
print("ok grader: stale check and negation")

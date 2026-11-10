"""Implementation test for Chapter 13: the boundary holds when the model is fooled,
held-out variants run after the fix, and every fixed attack stays blocked."""
import _path  # noqa: F401

import security as S

ASHA = {"customer": "asha", "tenant": "a", "task": "refund_request"}
FIX = S.Filter([r"ignore (all )?previous instructions"])


def test_boundary_holds_when_fooled():
    for x in S.KNOWN + S.HELD_OUT + S.MULTI_TURN + [S.POISONED_MEMORY]:
        r = S.run_attack(x, S.Filter(), ASHA)
        assert r["obeyed"], x["id"]            # the stub is fooled every time
        assert (r["tool"], r["why"]) == ("refused", "caller mismatch"), x["id"]
    print("test_boundary_holds_when_fooled: OK")


def test_trusting_tool_is_the_break():
    r = S.run_attack(S.KNOWN[0], S.Filter(), ASHA, trusting=True)
    assert r["tool"] == "issued" and S.ORDERS[r["target"]]["owner"] != "asha"
    print("test_trusting_tool_is_the_break: OK")


def test_identity_from_session_not_model():
    assert S.issue_refund(ASHA, "2001") == ("issued", "")
    assert S.issue_refund(ASHA, "2002") == ("held", "needs approval")
    assert S.issue_refund({"customer": "ravi"}, "2001")[1] == "caller mismatch"
    print("test_identity_from_session_not_model: OK")


def test_task_authorization_and_disclosure():
    ship = dict(ASHA, task="delivery_status")
    r = S.run_attack(S.WRONG_TASK, S.Filter(), ship)
    assert r["obeyed"] and r["target"] == "2001"            # same customer's order
    assert (r["tool"], r["why"]) == ("refused", "task delivery_status: no refund")
    assert S.issue_refund(ASHA, "2001") == ("issued", "")   # authorized refund works
    assert S.issue_refund({"customer": "asha"}, "2001")[0] == "refused"   # no task
    d = S.run_disclosure(S.DISCLOSURE, ship)
    assert d["obeyed"] and (d["tool"], d["why"]) == ("refused", "caller mismatch")
    assert S.order_details(ship, "2001")[0] == "shown"
    assert S.report([r, d]) == (2, 0)          # followed twice, harmful never
    print("test_task_authorization_and_disclosure: OK")


def test_known_attacks_stay_blocked():
    for x in S.KNOWN:
        assert S.run_attack(x, FIX, ASHA)["blocked"], x["id"]
    print("test_known_attacks_stay_blocked: OK")


def test_held_out_never_used_by_fix():
    ids = {x["id"] for x in S.KNOWN}
    assert not ids & {x["id"] for x in S.HELD_OUT + S.MULTI_TURN}
    print("test_held_out_never_used_by_fix: OK")


if __name__ == "__main__":
    test_boundary_holds_when_fooled()
    test_trusting_tool_is_the_break()
    test_identity_from_session_not_model()
    test_task_authorization_and_disclosure()
    test_known_attacks_stay_blocked()
    test_held_out_never_used_by_fix()

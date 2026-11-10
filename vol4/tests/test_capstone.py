"""Implementation test for Chapter 16: the report keeps the consumed budget, every
critical invariant is checked, an escalate-everything run fails, the sealed week is
unchanged."""
import _path  # noqa: F401

import capstone as C

SCN, DEC = C.load("practice_week.json"), C.load("decisions.json")


def test_rerun_does_not_refund_budget():
    rep = C.run_week(SCN, DEC)
    assert rep["rerun"]["wrong"] < rep["incident"]["wrong"]
    assert rep["incident"]["lat_bad"] > rep["allowed_bad"]   # spent, and stays spent
    print("test_rerun_does_not_refund_budget: OK")


def test_restore_invariants_checked():
    bad = dict(DEC, restore={"choice": "resume_now"})
    crit = C.run_week(SCN, bad)["critical"]
    assert any(c.startswith("duplicate_refund") for c in crit)
    assert "deleted_customer_back asha" in crit
    assert C.graduation(C.run_week(SCN, bad), SCN)
    print("test_restore_invariants_checked: OK")


def test_escalate_everything_fails():
    rep = C.run_week(SCN, DEC, escalate_all=True)
    assert rep["incident"]["resolve"] == 0.0 and C.graduation(rep, SCN)
    print("test_escalate_everything_fails: OK")


def test_cost_limit_enforced():
    bad = dict(DEC, cost={"choice": "all_primary"})
    assert any("cost" in f for f in C.graduation(C.run_week(SCN, bad), SCN))
    print("test_cost_limit_enforced: OK")


def test_sealed_week_unchanged():
    assert C.sealed_ok()
    print("test_sealed_week_unchanged: OK")


def test_status_lines_separate_verdicts():
    rep = C.run_week(SCN, C.load("decisions.json"))
    lines = C.status_lines(rep, SCN)
    assert lines[0].startswith("Safety invariants: PASS")
    assert lines[1] == "Resolution and daily cost: PASS"
    assert "Latency SLO: BREACHED - 33 slow / 2 allowed of 200 eligible" in lines
    assert "Quality SLO: MET - 2 wrong / 7 allowed of 150 replies sent" in lines
    assert lines[-1] == "Release policy: FREEZE RISKY CHANGES"
    assert rep["allowed_bad"] == 200 * 10 // 1000 and rep["q_allowed"] == 150 * 50 // 1000
    print("test_status_lines_separate_verdicts: OK")


if __name__ == "__main__":
    test_rerun_does_not_refund_budget()
    test_restore_invariants_checked()
    test_escalate_everything_fails()
    test_cost_limit_enforced()
    test_sealed_week_unchanged()
    test_status_lines_separate_verdicts()

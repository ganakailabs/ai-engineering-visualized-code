"""Implementation test for Chapter 15: the drill names the failing box, reconciliation
finds every outstanding entry without paying twice, and recovery is checked on the
original failing cases."""
import _path  # noqa: F401

import incident as I


def _failing(w, kind):
    return [c for c in I.cases() if c["kind"] == kind and not I.run_case(w, c)["ok"]]


def test_drill_names_the_box():
    for fault, kind, box in (("stale_index", "policy", "DATA"),
                             ("breaker_stuck", "courier", "TOOL")):
        w = I.world(fault)
        boxes = {b for c in _failing(w, kind) for b, _ in I.triage(I.run_case(w, c))}
        assert boxes == {box}, (fault, boxes)
    print("test_drill_names_the_box: OK")


def test_model_swap_does_not_fix_stale_data():
    w = I.world("stale_index")
    assert I.rate(dict(w, model="stub-b"), "policy") == I.rate(w, "policy")
    print("test_model_swap_does_not_fix_stale_data: OK")


def test_reconcile_finds_every_outstanding_entry():
    ledger, payments = I.ledger_midflight()
    outstanding = {k for k, s in ledger.items() if s in ("UNKNOWN", "SUBMITTED")}
    todo, conf, miss = I.reconcile(ledger, payments)
    assert todo == len(outstanding) == conf + miss
    assert all(s == "DONE" for s in ledger.values())
    assert all(payments[k] == 1 for k in ledger)          # nobody paid twice
    print("test_reconcile_finds_every_outstanding_entry: OK")


def test_recovery_verified_on_original_cases():
    for fault, kind in (("stale_index", "policy"), ("breaker_stuck", "courier")):
        w = I.world(fault)
        failing = _failing(w, kind)
        assert failing
        fixed = I.recover(w, fault)
        assert all(I.run_case(fixed, c)["ok"] for c in failing)
        crit = I.critical_slice({c["id"] for c in failing})
        assert crit and not {c["id"] for c in crit} & {c["id"] for c in failing}
        assert all(I.run_case(fixed, c)["ok"] for c in crit)
    assert I.RUNBOOK["policy_cited"]["watch"]["minutes"] > 0   # a bounded window
    print("test_recovery_verified_on_original_cases: OK")


if __name__ == "__main__":
    test_drill_names_the_box()
    test_model_swap_does_not_fix_stale_data()
    test_reconcile_finds_every_outstanding_entry()
    test_recovery_verified_on_original_cases()

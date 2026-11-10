"""Chapter 15 exercise: Unstick the breaker.

The courier breaker is stuck open while refunds are mid-flight. Predict first: which
box does triage name, and how many ledger entries need reconciling? TOOL, and every
UNKNOWN entry. Contain (pause courier jobs), triage, reconcile before resuming, then
verify on the cases that failed. SIMULATED world (incident.py).
"""
import _path  # noqa: F401

import incident as I

w = I.world("breaker_stuck")
rb = I.RUNBOOK["courier_resolved"]
ok, n = I.rate(w, "courier")
print(f"alert courier_resolved={ok / n:.2f} < slo {rb['slo']:.2f}")
w["paused"].add("courier")
print(f"contain {rb['contain'][0]} -> paused={sorted(w['paused'])}")

failing = [c for c in I.cases() if c["kind"] == "courier"
           and not I.run_case(w, c)["ok"]]
found = I.triage(I.run_case(w, failing[0]))
print(f"triage {found[0][0]} {found[0][1]}")
assert [b for b, _ in found] == ["TOOL"]

ledger, payments = I.ledger_midflight()
todo, conf, miss = I.reconcile(ledger, payments)
print(f"reconcile ledger unknown={todo} -> confirmed={conf} not_found={miss}")
assert todo == conf + miss and all(v == 1 for v in payments.values())

w = I.recover(w, "breaker_stuck")
w["paused"].discard("courier")
passed = sum(I.run_case(w, c)["ok"] for c in failing)
print(f"verify original cases pass={passed}/{len(failing)}; resumed")
assert passed == len(failing)
print("ch15 solution: OK")

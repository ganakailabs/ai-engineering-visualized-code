"""Chapter 15: Incident Response: Contain, Recover, Verify.

Run from the repo root:  python3 vol4/ch15.py
A SIMULATED incident (incident.py): the retrieval index is three days older than the
returns policy. Part 1: alert, severity, owner, containment. Part 2: the BREAK (swap the
model) and the FIX (triage by box). Part 3: recover, reconcile the ledger, verify on
the original failing cases, watch the SLO. Comms updates are drafts; nothing is sent.
"""
import _root  # noqa: F401

import incident as I

if __name__ == "__main__":
    print("== Part 1: alert, severity, owner, contain ==")
    w = I.world("stale_index")
    ok, n = I.rate(w, "policy")
    rb = I.RUNBOOK["policy_cited"]
    print(f"alert policy_cited={ok / n:.2f} < slo {rb['slo']:.2f} "
          f"(simulated, {n} cases)")
    sev = I.severity(money_wrong=False, customers_affected=True)
    print(f"alert policy_cited down severity={sev} owner={rb['owner']} "
          f"on_call={rb['on_call']}")
    w["flags"]["new_policy_prompt"], w["held"] = False, True
    print("contain flag=new_policy_prompt off")
    print("contain policy replies held for review (harm stopped)")
    ok2, _ = I.rate(w, "policy")
    print(f"after flag off policy_cited={ok2 / n:.2f} (flag was not it)")
    print("comms update 1 drafted: impact, severity, next update")

    print("== Part 2: find the box ==")
    swapped = dict(w, model="stub-b")
    ok3, _ = I.rate(swapped, "policy")
    print(f"BREAK swap model stub-a -> stub-b: policy_cited="
          f"{ok3 / n:.2f} (unchanged)")
    failing = [c for c in I.cases() if c["kind"] == "policy"
               and not I.run_case(w, c)["ok"]]
    t = I.run_case(w, failing[0])
    print(f"FIX walk the trace of {t['case']}:")
    bad = dict(I.triage(t))
    for box in I.BOXES:
        print(f"  {box:<8}{bad.get(box, 'ok')}")
    box = next(b for b in I.BOXES if b in bad)
    print(f"triage {box.lower()} {bad[box]}")

    print("== Part 3: recover, reconcile, verify ==")
    ledger, payments = I.ledger_midflight()
    w = I.recover(w, "stale_index")
    print(f"recover: workers paused; index restored from source "
          f"{w['index_date']}")
    todo, conf, miss = I.reconcile(ledger, payments)
    print(f"restore -> reconcile ledger unknown={todo} -> "
          f"confirmed={conf} not_found={miss}")
    dup = sum(v > 1 for v in payments.values())
    print(f"ledger DONE={sum(s == 'DONE' for s in ledger.values())}/20 "
          f"double payments={dup}; workers resumed")
    passed = sum(I.run_case(w, c)["ok"] for c in failing)
    print(f"verify original cases pass={passed}/{len(failing)}")
    crit = I.critical_slice({c["id"] for c in failing})
    cpass = sum(I.run_case(w, c)["ok"] for c in crit)
    print(f"verify untouched critical slice pass={cpass}/{len(crit)}")
    wt = rb["watch"]
    print(f"release hold for {wt['share']:.0%} of policy replies; "
          f"{wt['who']} watches {wt['minutes']} min")
    ok4, n4 = I.rate(w, "policy")
    print(f"  watch policy_cited={ok4 / n4:.2f} >= {rb['slo']:.2f}, "
          f"critical failures={len(crit) - cpass} (simulated rerun)")
    w["held"], w["flags"]["new_policy_prompt"] = False, True
    print("release hold fully; flag back on after the window")
    print("comms update 2 drafted (not sent): fixed, verified")

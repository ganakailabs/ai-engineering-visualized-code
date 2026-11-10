"""Chapter 16: Capstone: Operating the Complete System.

Run from the repo root:  python3 vol4/ch16.py
The PRACTICE week (capstone/practice_week.json), all SIMULATED: seeded tickets, a
scripted provider update, a stale index and a restore, under a fixed daily cost limit.
Part 1: the decision record. Part 2: one day traced (Watch the Agent). Part 3: the
BREAK (the rerun reported as the week) and the FIX (three windows, budget kept).
The sealed week is opened only by the exercise (solutions/ch16_solution.py).
"""
import _root  # noqa: F401

import capstone as C

if __name__ == "__main__":
    scn, dec = C.load("practice_week.json"), C.load("decisions.json")
    print(f"== Part 1: {scn['name']} (simulated), decision record ==")
    for k in ("provider_update", "stale_index", "restore", "cost"):
        print(f"decide {k:<16}{dec[k]['choice']}")
    rep = C.run_week(scn, dec)

    print("== Part 2: watch one day (tue, simulated) ==")
    tue = [r for r in rep["records"] if r["day"] == "tue"]
    lag = scn["detect_after"]
    wrong_before = sum(r["outcome"] == "wrong" for r in tue if r["i"] < lag)
    held = sum(r["kind"] == "policy" and r["outcome"] == "escalated"
               and r["model"] != "fallback" and r["i"] >= lag for r in tue)
    print(f"alert  tue-{lag:02d} policy answers wrong={wrong_before} "
          f"since tue-00")
    print(f"contain hold returns answers for review: held={held}")
    first = next(r for r in tue if r["outcome"] == "wrong")
    box, why = C.triage(first, scn)[0]
    print(f"triage {box} {why} (scripted world)")
    print("fix    index rebuilt overnight; readiness checks index age")
    fixed = dict(scn, events=[e for e in scn["events"]
                              if e["type"] != "stale_index"])
    re_tue = [C.handle(t, fixed, dec, lag=0) for t in C.tickets(scn)
              if t["day"] == "tue"]
    print(f"rerun  tue tickets on the fixed system: wrong="
          f"{sum(r['outcome'] == 'wrong' for r in re_tue)}")
    print("report three windows, below")

    print("== Part 3: the report ==")
    rr = rep["rerun"]
    print(f"BREAK week from rerun only: wrong={rr['wrong']} "
          f"resolve={rr['resolve']:.2f} -> 'green week'")
    print(f"{'window':<10}{'tickets':>8}{'slow':>6}{'wrong':>7}"
          f"{'resolve':>9}{'cost/day':>10}")
    for w in ("incident", "rerun", "recovery"):
        x = rep[w]
        print(f"{w:<10}{x['n']:>8}{x['lat_bad']:>6}{x['wrong']:>7}"
              f"{x['resolve']:>9.2f}{x['max_day_cost']:>10.1f}")
    print("status (a decision simulation; every count is simulated):")
    for line in C.status_lines(rep, scn):
        print(line)
    esc = C.graduation(C.run_week(scn, dec, escalate_all=True), scn)
    print(f"escalate-everything run: {'FAIL' if esc else 'pass'} ({esc[0]})")

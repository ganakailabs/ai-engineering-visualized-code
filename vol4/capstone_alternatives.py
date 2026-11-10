"""Capstone appendix: the practice week under each alternative decision.

Run from the repo root:  python3 vol4/capstone_alternatives.py
Changes one decision at a time from capstone/decisions.json and reports the incident
window, the cost limit, the graduation checks, and, separately, each SLO budget's status
and the release policy it triggers. Practice week only (SIMULATED);
the sealed week stays unopened.
"""
import _root  # noqa: F401

import capstone as C

ALTERNATIVES = [("provider_update", "wait"), ("provider_update", "route_fallback"),
                ("stale_index", "ignore"), ("restore", "resume_now"),
                ("cost", "all_primary")]

if __name__ == "__main__":
    scn, dec = C.load("practice_week.json"), C.load("decisions.json")
    print(f"{scn['name']} (simulated); one change at a time")
    print(f"{'change':<31}{'slow':>5}{'wrong':>6}{'resolve':>8}{'crit':>5}"
          f"{'cost':>6}")
    rows = [("author's record", dec)] + [
        (f"{k}={v}", dict(dec, **{k: {"choice": v}})) for k, v in ALTERNATIVES]
    for name, d in rows:
        rep = C.run_week(scn, d)
        cost = max(rep["incident"]["max_day_cost"], rep["recovery"]["max_day_cost"])
        x = rep["incident"]
        print(f"{name:<31}{x['lat_bad']:>5}{x['wrong']:>6}{x['resolve']:>8.2f}"
              f"{len(rep['critical']):>5}{cost:>6.1f}")
        fails = C.graduation(rep, scn)
        lat = rep["incident"]["lat_bad"] + rep["recovery"]["lat_bad"]
        q = rep["incident"]["wrong"] + rep["recovery"]["wrong"]
        lat_s = "BREACHED" if lat > rep["allowed_bad"] else "met"
        q_s = "BREACHED" if q > rep["q_allowed"] else "met"
        policy = "FREEZE" if "BREACHED" in (lat_s, q_s) else "normal"
        print(f"  -> checks {'pass' if not fails else 'FAIL: ' + fails[0]}")
        print(f"     latency {lat}/{rep['allowed_bad']} {lat_s}, quality "
              f"{q}/{rep['q_allowed']} {q_s} -> release policy {policy}")
    print(f"limits: resolve>={scn['resolve_min']:.2f} "
          f"cost<={scn['cost_units_per_day']}/day critical=0")

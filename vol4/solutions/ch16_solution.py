"""Chapter 16 exercise: Run the sealed week (graduation).

Open the sealed week, run it with YOUR decision record (capstone/decisions.json), and
report it in three windows. Predict first: which SLO breaks first, and what will you
trade to hold the safety invariants? This checks the report and the invariants, not
one fixed answer: any decision record that passes these checks passes.
All SIMULATED (capstone.py). Do not tune on the sealed week; that is what the hash
is for.
"""
import _path  # noqa: F401

import capstone as C

assert C.sealed_ok(), "sealed_week.json changed since it was sealed"
scn, dec = C.load("sealed_week.json"), C.load("decisions.json")
print("sealed week opened (hash ok)")
rep = C.run_week(scn, dec)
for w in ("incident", "rerun", "recovery"):
    x = rep[w]
    print(f"{w:<9} slow={x['lat_bad']} wrong={x['wrong']} "
          f"resolve={x['resolve']:.2f} cost/day={x['max_day_cost']:.1f}")
used = rep["incident"]["lat_bad"] + rep["recovery"]["lat_bad"]
qused = rep["incident"]["wrong"] + rep["recovery"]["wrong"]
print(f"budget latency used={used}/{rep['allowed_bad']} "
      f"quality used={qused}/{rep['q_allowed']}")
print("budget reported per window: latency, quality")

# graduation: zero critical; resolution at or above the minimum; within the cost
# limit; the consumed budget comes from the incident window, not the rerun
print(f"invariants critical={len(rep['critical'])}")
assert not rep["critical"]
fails = C.graduation(rep, scn)
ok_inc = rep["incident"]["resolve"] >= scn["resolve_min"]
ok_rec = rep["recovery"]["resolve"] >= scn["resolve_min"]
print(f"resolve incident>=min: {'yes' if ok_inc else 'no'} "
      f"recovery>=min: {'yes' if ok_rec else 'no'}")
assert not fails, fails
assert used == rep["incident"]["lat_bad"] + rep["recovery"]["lat_bad"]  # not rerun
esc = C.graduation(C.run_week(scn, dec, escalate_all=True), scn)
print(f"escalate-everything run fails: {'yes' if esc else 'no'}")
assert esc
print("ch16 solution: OK")

"""Chapter 10: Model Routing, Fallbacks and Provider Resilience.

Run from the repo root:  python3 vol4/ch10.py
Part 1 routes each ticket type to the cheapest model that passes its bar (MM-129).
Part 2 shows the untested fallback (BREAK) and the eligibility check (FIX), then runs
a simulated noon outage of the primary provider (MM-130). The catalogue, prices and
bake-off scores are examples (simulated), not measurements of real models.
"""
import _root  # noqa: F401

import routing as R
from service import refund_rule
from store import ORDERS

NOON = [  # simulated tickets arriving during the outage (tenant e is in the EU)
    {"id": "T-faq-e1", "tenant": "e", "route": "faq", "deadline_left_s": 50},
    {"id": "T-del-a1", "tenant": "a", "route": "delivery", "deadline_left_s": 40},
    {"id": "T-del-a2", "tenant": "a", "route": "delivery", "deadline_left_s": 4},
    {"id": "T-ref-a3", "tenant": "a", "route": "refund", "deadline_left_s": 45,
     "order_id": "4410"},
]

# One minute of noon traffic at the expected failover load (simulated mix).
DRILL = ([{"id": f"F{i}", "tenant": "e" if i < 10 else "a", "route": "faq",
           "deadline_left_s": 40} for i in range(60)] +
         [{"id": f"D{i}", "tenant": "a", "route": "delivery", "deadline_left_s": 40}
          for i in range(40)] +
         [{"id": f"R{i}", "tenant": "a", "route": "refund", "deadline_left_s": 40}
          for i in range(20)])
DRILL_CAPACITY = {"backup": 50, "local": 20}   # example fallback rate limits

if __name__ == "__main__":
    print("== Part 1: the model router (MM-129), example scores ==")
    for route, r in R.ROUTES.items():
        m = R.route_model(route)
        print(f"route-model type={route:8} model={m:6} bar=pass "
              f"({R.BAKEOFF[(route, m)]}>={r['bar']})")
    routed = sum(R.MODELS[R.route_model(x)]["cost"] for x in R.ROUTES) / len(R.ROUTES)
    print(f"cost per call, one of each type: routed={routed:.2f} "
          f"all-large={R.MODELS['large']['cost']:.2f}")
    print("  (simulated units; scores are examples, not measurements)")
    print(f"scorecard route=refund bar=950, n={R.CASES} cases each (simulated):")
    for m in ("mini", "small", "medium", "large"):
        c = R.scorecard("refund", m)
        print(f"  {m:6} {c['score']} [{c['lo']},{c['hi']}] crit={c['critical'][0]}/"
              f"{c['critical'][1]} p95={c['p95_s']}s cost/res={c['cost_resolved']:.2f}"
              f" -> {c['verdict']}")

    print("== Part 2a: untested fallback (BREAK) ==")
    t = NOON[3]
    print(f"naive: primary down, refund #{t['order_id']} -> backup, no checks")
    print(f"  reply: \"{R.stub_reply('backup', t)}\"")
    ok, clause = refund_rule(ORDERS[t["order_id"]])
    print(f"  refund_rule: {'yes' if ok else 'no'} ({clause} final sale) -> WRONG")
    print("== Part 2b: noon outage, eligibility checked (simulated) ==")
    for t in NOON:
        print(f"ticket {t['id']} tenant={t['tenant']} route={t['route']}")
        R.handle(t, {"primary": "quota"}, lambda s: print("  " + s))
    print("ticket T-faq-a4 tenant=a route=faq, a rate limit, not a quota")
    R.handle({"id": "T-faq-a4", "tenant": "a", "route": "faq", "deadline_left_s": 30},
             {"primary": 20}, lambda s: print("  " + s), retries=1)

    print("== Part 2c: outage drill at failover load (simulated) ==")
    out, retries = R.outage_drill(DRILL, DRILL_CAPACITY)
    print(f"1 minute, {len(DRILL)} tickets, primary out of quota; "
          f"backup {DRILL_CAPACITY['backup']}/min, local {DRILL_CAPACITY['local']}/min")
    print(f"  served backup={out.get('backup', 0)} local={out.get('local', 0)}, "
          f"escalated={out.get('escalate', 0)}, retries taken={retries}")

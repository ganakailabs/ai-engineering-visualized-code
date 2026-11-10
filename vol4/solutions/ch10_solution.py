"""Chapter 10 exercise: Route disputes with no backup.

Add a dispute route that only the large model passes, with no fallback ever tested on
it. Predict first: what happens to a dispute at noon, when the primary provider is out
of quota? The dispute escalates with a clear reason; FAQ and delivery tickets keep being
served by their tested fallbacks. Scores are examples (simulated); route quality per
model is a model experiment, unmeasured here: run it on your replay set.
"""
import _path  # noqa: F401

import routing as R

routes = dict(R.ROUTES, dispute=dict(bar=970, tools=True, json=True, ctx=8000))
R.BAKEOFF[("dispute", "large")] = 975          # example score; no fallback tested
lines = []
noon = [
    {"id": "T-dis-a1", "tenant": "a", "route": "dispute", "deadline_left_s": 50},
    {"id": "T-faq-a2", "tenant": "a", "route": "faq", "deadline_left_s": 50},
    {"id": "T-del-a3", "tenant": "a", "route": "delivery", "deadline_left_s": 50},
]
print(f"route-model type=dispute model={R.route_model('dispute', routes)}")
got = {}
for t in noon:
    got[t["id"]] = R.handle(t, {"primary": "quota"}, lines.append, routes)
    print(f"noon {t['id']} -> {got[t['id']]}")
for s in lines:
    if "dispute" in s:
        print("  " + s)
assert R.route_model("dispute", routes) == "large"
assert got == {"T-dis-a1": "escalate", "T-faq-a2": "backup", "T-del-a3": "backup"}
assert "escalate T-dis-a1 route=dispute reason=no eligible model" in lines
print("ch10 solution: OK")

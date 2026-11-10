"""Tests for routing.py (Chapter 10): each eligibility rule refuses one named fallback."""
import _path  # noqa: F401

import routing as R

assert R.route_model("faq") == "small"
assert R.route_model("refund") == "medium"           # small misses the 950 bar
assert R.route_model("warranty") == "large"


def t(route, tenant="a", left=50):
    return {"id": "T", "tenant": tenant, "route": route, "deadline_left_s": left}


assert R.eligible("local", t("refund")) == (False, "untested route=refund")
R.BAKEOFF[("refund", "backup")] = 960                # pretend it was tested...
assert R.eligible("backup", t("refund")) == (False, "capability tools=no")
del R.BAKEOFF[("refund", "backup")]
R.BAKEOFF[("refund", "local")] = 960                 # ...and here: no JSON mode
assert R.eligible("local", t("refund")) == (False, "capability json=no")
del R.BAKEOFF[("refund", "local")]
assert R.eligible("backup", t("faq", "e")) == (False, "data_boundary=eu")
assert R.eligible("backup", t("delivery", left=4))[1].startswith("left=4s")
assert not R.eligible("backup", t("delivery", left=8))[0]   # 8-3 reserve < 6 p95
assert R.eligible("backup", t("delivery", left=9))[1].endswith("timeout=6s")
assert R.eligible("backup", t("delivery"))[0]

# a cheap candidate passing the average bar but failing a critical case is rejected
mini = R.scorecard("refund", "mini")
assert mini["score"] >= 950 and mini["verdict"] == "reject: critical"
assert mini["cost_resolved"] < R.scorecard("refund", "medium")["cost_resolved"]
assert R.route_model("refund") == "medium"
# the 955 that passes a 950 bar has an interval reaching below the bar
med = R.scorecard("refund", "medium")
assert med["lo"] < 950 < med["score"]

# a fallback that cannot fit the remaining time after the reserve is refused
log = []
assert R.handle(t("delivery", left=7), {"primary": "quota"}, log.append) == "escalate"
# outage drill: capacity, not one success, decides where tickets go
cap = {"backup": 2, "local": 0}
out, retries = R.outage_drill([t("faq")] * 3, cap)
assert out == {"backup": 2, "escalate": 1} and retries == 2

log = []
assert R.handle(t("faq"), {"primary": 20}, log.append, retries=1) == "escalate"
assert log[-1] == "escalate T reason=retry budget spent"      # budget rule
assert R.handle(t("faq"), {}, log.append) == "small"          # no outage: primary
print("test_routing: OK")

"""Capstone for Chapter 16: operate a week, then report it in three windows.

Everything is SIMULATED: seeded tickets, a scripted world with the scenario's events,
stub models with fixed latencies and costs. Numbers show how the report is built and
how decisions trade against each other, not real performance.

MM-143 The Weekly Improvement Loop (reporting format): the INCIDENT WINDOW (what
       customers got, budget consumed), the RERUN (the same tickets on the fixed system,
       counterfactual), and the RECOVERY window after release. A green rerun does not
       give back budget the incident window consumed.
"""
import hashlib
import json
import random
from pathlib import Path

import slo

HERE = Path(__file__).resolve().parent / "capstone"
SPEC = slo.load()["slos"]["latency"]           # first checked reply <= 60 s, 99.0% (Ch 2)
QUALITY_PERMILLE = slo.load()["slos"]["quality"]["target_permille"]
APPROVAL_OVER = 100

# simulated stub models: first-reply seconds, cost units per ticket
MODELS = {"primary": (20, 0.8), "primary_slow": (75, 0.8),
          "fallback": (25, 0.5), "small": (10, 0.3), "human_queue": (15, 0.1)}


def load(name):
    return json.loads((HERE / name).read_text())


def sealed_ok(path=HERE / "sealed_week.json"):
    want = (HERE / "SEALED.sha256").read_text().strip()
    return hashlib.sha256(path.read_bytes()).hexdigest() == want


def tickets(scn):
    rng = random.Random(scn["seed"])
    kinds = (["refund"] * 15 + ["status"] * 10 + ["policy"] * 10
             + ["unanswerable"] * 5)
    out = []
    for day in scn["days"]:
        order = kinds[:]
        rng.shuffle(order)
        for i, k in enumerate(order):
            t = {"id": f"{day}-{i:02d}", "day": day, "i": i, "kind": k}
            if k == "refund":
                t["amount"] = rng.choice([20, 40, 60, 90, 150, 300])
            if k == "policy":
                t["topic"] = rng.choice(["returns", "warranty"])
            t["solvable"] = k in ("status", "policy") or (
                k == "refund" and t["amount"] <= APPROVAL_OVER)
            out.append(t)
    return out


def _active(ev, t, days):
    d, s = days.index(t["day"]), days.index(ev["day"])
    end = days.index(ev["until"]) if "until" in ev else s + 1
    return (d > s or (d == s and t["i"] >= ev["at"])) and d < end


def _detected(ev, t, days, lag):
    """Decisions apply only after the alert: `lag` tickets after the event starts."""
    d, s = days.index(t["day"]), days.index(ev["day"])
    return d > s or t["i"] >= ev["at"] + lag


def handle(t, scn, dec, lag=None, escalate_all=False):
    """-> record: model, first_reply_s, cost, outcome (resolved/escalated/wrong)."""
    days, lag = scn["days"], scn["detect_after"] if lag is None else lag
    on = {e["type"]: e for e in scn["events"] if _active(e, t, days)}
    acted = {k for k, e in on.items() if _detected(e, t, days, lag)}
    model = "primary"
    if dec["cost"]["choice"] == "small_for_status" and t["kind"] == "status":
        model = "small"
    if "provider_update" in on and model == "primary":
        model = "primary_slow"
        choice = dec["provider_update"]["choice"]
        if "provider_update" in acted and (
                choice == "route_fallback" or
                (choice == "fallback_except_policy" and t["kind"] != "policy")):
            model = "fallback"
    outcome = "resolved"
    if not t["solvable"]:
        outcome = "escalated"                       # expected escalation, honoured
    elif t["kind"] == "policy":
        if model == "fallback":
            outcome = "escalated"                   # fallback abstains on policy
        elif "stale_index" in on and t["topic"] == "returns":
            hold = "stale_index" in acted and \
                dec["stale_index"]["choice"] == "hold_returns"
            outcome = "escalated" if hold else "wrong"
    if escalate_all or outcome == "escalated":
        outcome, model = "escalated", "human_queue" if escalate_all else model
    secs, cost = MODELS[model]
    return {**t, "model": model, "first_reply_s": secs, "cost": cost,
            "outcome": outcome, "tenant_id": "northwind", "cancelled": False}


BOX = {"stale_index": "DATA", "provider_update": "MODEL", "restore": "TOOL"}


def triage(record, scn):
    """Scripted triage: the box of the scenario event active on this ticket. In the
    Chapter 15 code the box comes from walking the trace; here the world is scripted,
    so the event is known."""
    symptom = {"wrong": "stale_index"}.get(record["outcome"]) or (
        "provider_update" if record["first_reply_s"] > SPEC["threshold_s"] else None)
    on = [e["type"] for e in scn["events"] if _active(e, record, scn["days"])]
    return [(BOX[e], e) for e in on if e == symptom]


def restore_checks(scn, dec):
    """Critical invariants touched by a restore: duplicate refunds and deleted
    customers back. Returns a list of violations (empty is the only pass)."""
    bad = []
    for e in scn["events"]:
        if e["type"] != "restore":
            continue
        if dec["restore"]["choice"] != "reconcile_and_replay":
            # resume without checking: an UNKNOWN that had reached the provider is
            # paid again, and deleted customers come back from the backup
            bad.append(f"duplicate_refund ({e['day']})")
            bad += [f"deleted_customer_back {c}" for c in e["deleted_customers"]]
    return bad


def window(records, scn):
    lat = slo.latency(records, SPEC)
    replies = [r for r in records if r["outcome"] != "escalated"]
    wrong = sum(r["outcome"] == "wrong" for r in records)
    solv = [r for r in records if r["solvable"]]
    resolved = sum(r["outcome"] == "resolved" for r in solv)
    days = sorted({r["day"] for r in records})
    spend = {d: sum(r["cost"] for r in records if r["day"] == d) for d in days}
    return {"n": len(records), "lat_bad": lat["bad"],
            "wrong": wrong, "replies": len(replies),
            "resolved": resolved, "solvable": len(solv),
            "resolve": resolved / len(solv) if solv else 0.0,
            "max_day_cost": max(spend.values()) if spend else 0.0}


def run_week(scn, dec, escalate_all=False):
    ts = tickets(scn)
    inc = [t for t in ts if t["day"] in scn["incident_days"]]
    rec = [t for t in ts if t["day"] not in scn["incident_days"]]
    hist = [handle(t, scn, dec, escalate_all=escalate_all) for t in inc]
    # counterfactual: the same tickets, decisions in force from the first ticket and
    # the readiness check that now refuses a stale index (the incident's action item)
    fixed = dict(scn, events=[e for e in scn["events"] if e["type"] != "stale_index"])
    rerun = [handle(t, fixed, dec, lag=0, escalate_all=escalate_all) for t in inc]
    after = [handle(t, fixed, dec, lag=0, escalate_all=escalate_all) for t in rec]
    eligible = len(ts)
    allowed = eligible * (1000 - SPEC["target_permille"]) // 1000
    replies = sum(r["outcome"] != "escalated" for r in hist + after)
    q_allowed = replies * (1000 - QUALITY_PERMILLE) // 1000
    return {"incident": window(hist, scn), "rerun": window(rerun, scn),
            "recovery": window(after, scn), "allowed_bad": allowed,
            "eligible": eligible, "q_allowed": q_allowed, "q_eligible": replies,
            "critical": restore_checks(scn, dec), "records": hist}


def graduation(rep, scn):
    """-> list of failed checks (empty passes). Uses the INCIDENT and RECOVERY
    windows; the rerun is evidence for the fix, not a substitute for the week."""
    fails = []
    if rep["critical"]:
        fails.append(f"critical invariants: {len(rep['critical'])}")
    for w in ("incident", "recovery"):
        if rep[w]["resolve"] < scn["resolve_min"]:
            fails.append(f"{w} resolve {rep[w]['resolve']:.2f} < "
                         f"{scn['resolve_min']:.2f}")
        if rep[w]["max_day_cost"] > scn["cost_units_per_day"]:
            fails.append(f"{w} cost {rep[w]['max_day_cost']:.1f}/day over limit")
    return fails


def status_lines(rep, scn):
    """The report's verdicts, one line each, with the denominators that produce them.
    Allowed counts round DOWN: allowed = floor(eligible x (1 - target))."""
    inc, rec = rep["incident"], rep["recovery"]
    restores = sum(e["type"] == "restore" for e in scn["events"])
    lat_used = inc["lat_bad"] + rec["lat_bad"]
    q_used = inc["wrong"] + rec["wrong"]
    lat_ok = lat_used <= rep["allowed_bad"]
    q_ok = q_used <= rep["q_allowed"]
    res_cost = [f for f in graduation(rep, scn) if "critical" not in f]
    out = [
        f"Safety invariants: {'PASS' if not rep['critical'] else 'FAIL'} "
        f"({len(rep['critical'])} violations; {restores} restore checked)",
        f"Resolution and daily cost: {'PASS' if not res_cost else 'FAIL'}",
        f"  resolved/solvable incident {inc['resolved']}/{inc['solvable']}="
        f"{inc['resolve']:.2f}, recovery {rec['resolved']}/{rec['solvable']}="
        f"{rec['resolve']:.2f} (min {scn['resolve_min']:.2f})",
        f"  max cost/day {max(inc['max_day_cost'], rec['max_day_cost']):.1f} "
        f"(limit {scn['cost_units_per_day']:.1f})",
        f"Latency SLO: {'MET' if lat_ok else 'BREACHED'} - {lat_used} slow / "
        f"{rep['allowed_bad']} allowed of {rep['eligible']} eligible",
        f"Quality SLO: {'MET' if q_ok else 'BREACHED'} - {q_used} wrong / "
        f"{rep['q_allowed']} allowed of {rep['q_eligible']} replies sent",
        "  allowed = floor(eligible x (1 - target)); used = incident + recovery",
        f"Release policy: {'NORMAL' if lat_ok and q_ok else 'FREEZE RISKY CHANGES'}",
    ]
    return out

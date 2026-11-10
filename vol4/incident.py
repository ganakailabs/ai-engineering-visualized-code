"""Incident response for Chapter 15: contain, triage by box, recover, reconcile, verify.

Everything here is SIMULATED: a scripted world with one injected fault, a stub model
that quotes whatever context it gets, and a mock payments record. The point is the
order of work and the checks, not any real failure rate.

MM-142 Incident Triage by Box: walk one failing trace box by box (CONTEXT, MODEL,
       CHECK, TOOL, DATA) and name the box whose evidence is wrong.
MM-168 Contain, Recover, Verify: stop the harm, recover the system and its
       outstanding actions, then prove the fix on the cases that failed.
"""
import copy

BOXES = ["CONTEXT", "MODEL", "CHECK", "TOOL", "DATA"]
SOURCE_DATE = "2026-10-15"              # returns policy v2 published (fictional)
POLICY = {"v1": "returns within 30 days", "v2": "returns within 45 days"}

# alert -> (owner, severity rule) ; owners are fictional rota names
RUNBOOK = {
    "policy_cited": {"owner": "support-eng", "on_call": "meera", "slo": 0.90,
                     "contain": ["flag new_policy_prompt off",
                                 "hold policy replies for review"],
                     # a bounded observation window before the hold is fully released
                     "watch": {"share": 0.10, "minutes": 120, "who": "meera",
                               "metrics": ["policy_cited", "critical failures"]}},
    "courier_resolved": {"owner": "platform", "on_call": "dev", "slo": 0.90,
                         "contain": ["pause courier jobs"]},
}


def severity(money_wrong, customers_affected):
    """1: money or data wrong. 2: customer-facing SLO breached. 3: internal only."""
    if money_wrong:
        return 1
    return 2 if customers_affected else 3


def world(fault=None):
    w = {"index_date": "2026-10-15", "flags": {"new_policy_prompt": True},
         "model": "stub-a", "breaker": "closed", "paused": set(),
         "held": False}
    if fault == "stale_index":
        w["index_date"] = "2026-10-12"
    if fault == "breaker_stuck":
        w["breaker"] = "open"
    return w


def cases():
    """Ten policy tickets (six about returns, the policy that changed) and ten courier
    status tickets. Fictional. `critical` marks the slice checked after every recovery
    even though the incident did not touch it."""
    out = [{"id": f"P{i}", "kind": "policy", "critical": i >= 6,
            "topic": "returns" if i < 6 else "warranty"} for i in range(10)]
    out += [{"id": f"C{i}", "kind": "courier", "critical": i < 4} for i in range(10)]
    return out


def critical_slice(failing_ids):
    """Critical cases the incident did not touch: a fix must not break them."""
    return [c for c in cases() if c["critical"] and c["id"] not in failing_ids]


def run_case(w, case):
    """-> trace: one structured record per box, plus the outcome."""
    t = {"case": case["id"], "kind": case["kind"]}
    if case["kind"] == "policy":
        stale = w["index_date"] < SOURCE_DATE and case["topic"] == "returns"
        version = "v1" if stale else "v2"
        chunk = POLICY[version] if case["topic"] == "returns" else "warranty 1 year"
        t["DATA"] = {"chunk_version": version, "index_date": w["index_date"],
                     "source_date": SOURCE_DATE if case["topic"] == "returns"
                     else w["index_date"]}
        t["CONTEXT"] = {"has_chunk": True, "prompt_flag":
                        w["flags"]["new_policy_prompt"]}
        t["MODEL"] = {"model": w["model"], "quoted": chunk}   # the stub quotes context
        t["TOOL"] = {"calls": 0}
        current = case["topic"] != "returns" or version == "v2"
        t["CHECK"] = {"verdict": "cited" if current else "outdated",
                      "recomputed": "cited" if current else "outdated"}
        t["ok"] = current
    else:
        open_ = w["breaker"] == "open"
        t["DATA"] = {"index_date": w["index_date"], "source_date": w["index_date"]}
        t["CONTEXT"] = {"has_chunk": True}
        t["MODEL"] = {"model": w["model"], "quoted": "status from tool"}
        t["TOOL"] = {"calls": 1, "status": "short_circuit" if open_ else "ok",
                     "breaker": w["breaker"]}
        t["CHECK"] = {"verdict": "fallback" if open_ else "resolved",
                      "recomputed": "fallback" if open_ else "resolved"}
        t["ok"] = not open_
    return t


def rate(w, kind, cs=None):
    cs = [c for c in (cs or cases()) if c["kind"] == kind]
    return sum(run_case(w, c)["ok"] for c in cs), len(cs)


def triage(trace):
    """Walk the boxes in order; return (box, evidence) for each box that is wrong."""
    found = []
    if not trace["CONTEXT"].get("has_chunk"):
        found.append(("CONTEXT", "retrieved chunk missing from prompt"))
    if trace["MODEL"]["quoted"] in ("", None):
        found.append(("MODEL", "reply ignores context"))
    if trace["CHECK"]["verdict"] != trace["CHECK"]["recomputed"]:
        found.append(("CHECK", "check verdict disagrees with recompute"))
    if trace["TOOL"].get("status") not in (None, "ok"):
        found.append(("TOOL", f"breaker {trace['TOOL']['breaker']} "
                      f"({trace['TOOL']['status']})"))
    d = trace["DATA"]
    if d["index_date"] < d["source_date"]:
        found.append(("DATA", f"STALE (index {d['index_date']} < "
                      f"source {d['source_date']})"))
    return found


# --- the ledger of outstanding actions ------------------------------------------

def ledger_midflight(n=20, unknown=("R-0007", "R-0013")):
    """Refunds in flight when workers were paused. Most finished; some are UNKNOWN:
    the worker sent the payment call and stopped before recording the receipt."""
    ledger, payments = {}, {}
    for i in range(1, n + 1):
        key = f"R-{i:04d}"
        if key in unknown:
            ledger[key] = "UNKNOWN"
        else:
            ledger[key] = "DONE"
            payments[key] = 1
    payments[unknown[0]] = 1            # this one reached the provider
    return ledger, payments


def reconcile(ledger, payments):
    """Check every UNKNOWN or SUBMITTED entry against the payments record before
    workers resume. Confirmed -> DONE. Not found -> retry once with the same key."""
    todo = [k for k, s in ledger.items() if s in ("UNKNOWN", "SUBMITTED")]
    confirmed = [k for k in todo if payments.get(k)]
    missing = [k for k in todo if not payments.get(k)]
    for k in confirmed:
        ledger[k] = "DONE"
    for k in missing:
        payments[k] = payments.get(k, 0) + 1      # same idempotency key
        ledger[k] = "DONE"
    return len(todo), len(confirmed), len(missing)


def recover(w, fault):
    w = copy.deepcopy(w)
    if fault == "stale_index":
        w["index_date"] = SOURCE_DATE           # rebuild from the source
    if fault == "breaker_stuck":
        w["breaker"] = "closed"                 # reset after a health probe passes
    return w

"""Chapter 2: SLOs and error budgets, with event accounting.

MM-118 The SLO Card: per SLO, the eligible events, the good events, the threshold,
       the window, the exclusions and an owner. Safety invariants sit on the card
       too, as pass/fail: they are never spent.
MM-162 The Error Budget: allowed bad events = (1 - target) x eligible events in the
       window. The release policy reads the budget; the budget does not act alone.
"""
import json
import re
from pathlib import Path

SLO_FILE = Path(__file__).resolve().parent / "slo.json"
# The same patterns as Vol 1 Ch 23 (PII), copied so this file stands alone.
PII = {"EMAIL": r"[\w.+-]+@[\w-]+\.[\w.]+",
       "PHONE": r"\+?\d[\d ]{8,}\d"}


def load(path=SLO_FILE):
    return json.loads(Path(path).read_text())


def eligible_latency(t):
    """Exclusions, written down: probes and tickets cancelled before any reply."""
    return t["tenant_id"] != "probe" and not t["cancelled"]


def budget(eligible, good, target_permille):
    """Integer arithmetic, so 99.0% of 403 is computed exactly; allowed bad rounds down."""
    allowed_bad = eligible * (1000 - target_permille) // 1000
    bad = eligible - good
    return {"eligible": eligible, "good": good, "bad": bad, "allowed_bad": allowed_bad,
            "remaining": allowed_bad - bad, "spent": bad > allowed_bad}


def latency(tickets, spec):
    events = [t for t in tickets if eligible_latency(t)]
    good = sum(1 for t in events if t["first_reply_s"] <= spec["threshold_s"])
    return budget(len(events), good, spec["target_permille"])


def burn_rate(bad, eligible, target_permille):
    """How fast a slice of time spends the budget: its bad share over the allowed share.
    1.0 spends the budget exactly over the window; above 1.0 it runs out early."""
    if not eligible:
        return 0.0
    return (bad / eligible) / ((1000 - target_permille) / 1000)


def invariant_violations(tickets):
    """Pass/fail. One violation is an incident; there is no allowance to spend."""
    return [t["ticket_id"] for t in tickets
            if any(re.search(p, t["reply"]) for p in PII.values())]


def cost_over(tickets, limit):
    return [t["ticket_id"] for t in tickets if t["tokens"] > limit]


RISKY = {"prompt", "model", "retrieval", "feature"}
SAFE = {"rollback", "reliability_fix"}


def release_allowed(kind, budgets, violations):
    """The written policy (slo.json "policy"), as code the release script calls."""
    if violations:
        if kind in SAFE:
            return True, "invariant broken -> fix or rollback allowed"
        return False, "invariant broken -> incident"
    if any(b["spent"] for b in budgets.values()) and kind in RISKY:
        return False, "budget spent -> freeze risky releases"
    if kind in RISKY:
        return True, "budget left"
    return True, "rollbacks and fixes always ship"

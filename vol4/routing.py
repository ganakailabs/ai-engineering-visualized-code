"""Chapter 10: model routing, fallbacks and provider resilience (MM-129, MM-130).

MM-129 The Model Router: each ticket type (route) has an eval bar; the router sends it
       to the cheapest model whose bake-off score on that route passes the bar.
MM-130 The Fallback Chain: when the primary provider fails, a fallback is used only if
       it is eligible for this ticket: tested on this route, capable (tools, structured
       output, context length), allowed to see this tenant's data, fast enough for the
       deadline left, and inside the ticket's retry budget. Otherwise: escalate.

A route's bar is necessary, not sufficient: the scorecard also records the case count
and an interval, the critical cases (every one must pass), the p95 latency and the cost
per resolved ticket. A p95 is an ADMISSION ESTIMATE; the call itself runs under an
enforced timeout of the time left minus RESERVE_S for the checks, persistence and send.

Everything here is a simulation. The catalogue, prices (made-up units, as in cost.py),
p95 latencies and bake-off scores are EXAMPLES, not measurements of any real model;
route quality per model is a model experiment, unmeasured here: run it on your replay set.
The retry budget is Vol 2's (cascade.RetryBudget): one pool per ticket, every layer
takes from it.
"""
import _root  # noqa: F401

from cascade import Exhausted, RetryBudget
from service import refund_rule
from store import ORDERS

# Example catalogue (simulated). provider = who hosts it.
MODELS = {
    "small": dict(provider="primary", cost=0.4, tools=True, json=True, ctx=16000, p95_s=2),
    "medium": dict(provider="primary", cost=1.0, tools=True, json=True, ctx=128000, p95_s=4),
    "large": dict(provider="primary", cost=3.0, tools=True, json=True, ctx=200000, p95_s=9),
    "backup": dict(provider="beta", cost=1.2, tools=False, json=True, ctx=128000, p95_s=6),
    "local": dict(provider="self", cost=0.3, tools=True, json=False, ctx=8000, p95_s=12),
    "mini": dict(provider="primary", cost=0.3, tools=True, json=True, ctx=16000, p95_s=2),
}
RESERVE_S = 3        # kept back from every deadline: output checks, persistence, send
HUMAN_COST = 80.0    # simulated units per escalated ticket (Chapter 9's human time)
CASES = 200          # eval cases per route in the example bake-off (simulated)
# Which tenant data regions each provider is approved for (fixture, fictional).
APPROVED = {"primary": {"eu", "in"}, "beta": {"in"}, "self": {"eu", "in"}}
TENANT_REGION = {"a": "in", "e": "eu"}
# Each route: its eval bar (permille) and what a model must be able to do.
ROUTES = {
    "faq": dict(bar=900, tools=False, json=False, ctx=3000),
    "delivery": dict(bar=900, tools=False, json=False, ctx=4000),
    "refund": dict(bar=950, tools=True, json=True, ctx=6000),
    "warranty": dict(bar=950, tools=True, json=True, ctx=6000),
}
# Example bake-off scores (permille), SIMULATED. A missing pair was never tested.
BAKEOFF = {
    ("faq", "small"): 940, ("faq", "medium"): 955, ("faq", "large"): 965,
    ("delivery", "small"): 910, ("delivery", "medium"): 945, ("delivery", "large"): 960,
    ("refund", "small"): 880, ("refund", "medium"): 955, ("refund", "large"): 970,
    ("warranty", "small"): 860, ("warranty", "medium"): 930, ("warranty", "large"): 960,
    ("faq", "backup"): 930, ("delivery", "backup"): 915, ("faq", "local"): 905,
    ("refund", "mini"): 960,         # a new cheap candidate, refunds only so far
}
# Critical action cases per route (passed, total), SIMULATED: money or policy moves.
# A candidate that fails any of them is rejected whatever its average.
CRITICAL = {
    ("refund", "mini"): (11, 12),    # approved one final-sale refund
    ("refund", "small"): (10, 12), ("refund", "medium"): (12, 12),
    ("refund", "large"): (12, 12), ("warranty", "small"): (9, 12),
    ("warranty", "medium"): (11, 12), ("warranty", "large"): (12, 12),
}
CHAIN = ["backup", "local"]          # spare tyres after the primary, in order


def wilson(k, n, z=1.96):
    """95% Wilson interval for k of n, as permille."""
    p, d = k / n, 1 + z * z / n
    c, h = (p + z * z / (2 * n)) / d, z * ((p * (1 - p) + z * z / (4 * n)) / n) ** 0.5 / d
    return round(1000 * (c - h)), round(1000 * (c + h))


def scorecard(route, model, routes=ROUTES, n=CASES):
    """One row of the route's scorecard. Cost per resolved ticket counts every case's
    call and a human for every failed case (simulated units, as in Chapter 9)."""
    score = BAKEOFF.get((route, model))
    if score is None:
        return None
    passed = round(score * n / 1000)
    crit = CRITICAL.get((route, model), (0, 0))
    cost = (n * MODELS[model]["cost"] + (n - passed) * HUMAN_COST) / n
    lo, hi = wilson(passed, n)
    bar = routes[route]["bar"]
    if score < bar:
        verdict = "reject: bar"
    elif crit[0] < crit[1]:
        verdict = "reject: critical"
    else:
        verdict = "pass"
    return dict(score=score, n=n, lo=lo, hi=hi, critical=crit, p95_s=MODELS[model]["p95_s"],
                cost_resolved=cost, verdict=verdict)


def route_model(route, routes=ROUTES):
    """Cheapest primary model whose scorecard passes: the bar AND every critical case."""
    ok = [m for m, s in MODELS.items() if s["provider"] == "primary"
          and (scorecard(route, m, routes) or {}).get("verdict") == "pass"]
    return min(ok, key=lambda m: MODELS[m]["cost"]) if ok else None


def eligible(model, ticket, routes=ROUTES):
    """(ok, reason) for using `model` on this ticket now. One rule per check."""
    r, m = routes[ticket["route"]], MODELS[model]
    score = BAKEOFF.get((ticket["route"], model))
    if score is None or score < r["bar"]:
        return False, f"untested route={ticket['route']}" if score is None \
            else f"bar {score}<{r['bar']}"
    for need in ("tools", "json"):
        if r[need] and not m[need]:
            return False, f"capability {need}=no"
    if r["ctx"] > m["ctx"]:
        return False, f"capability ctx={m['ctx']}<{r['ctx']}"
    region = TENANT_REGION[ticket["tenant"]]
    if region not in APPROVED[m["provider"]]:
        return False, f"data_boundary={region}"
    budget_s = ticket["deadline_left_s"] - RESERVE_S
    why = f"left={ticket['deadline_left_s']}s-{RESERVE_S}s reserve, p95={m['p95_s']}s"
    if budget_s < m["p95_s"]:
        return False, why
    return True, why + f", timeout={budget_s}s"


def stub_reply(model, ticket):
    """A stand-in for the model's reply. On refund routes the reply depends on the
    check_refund tool (code decides, from the order record); a model without tool
    calling cannot call it and answers from the ticket text alone."""
    oid = ticket.get("order_id")
    if ticket["route"] not in ("refund", "warranty"):
        return f"[{model}] answered {ticket['route']} question"
    if MODELS[model]["tools"]:
        ok, clause = refund_rule(ORDERS[oid])
        return f"Refund {'approved' if ok else 'declined'} for #{oid} ({clause})."
    return f"Refund approved for #{oid}."


def handle(ticket, provider_down, log, routes=ROUTES, retries=2, capacity=None):
    """Primary first; on failure walk the chain, eligible models only; else escalate.
    provider_down maps a provider to its error: "quota" (do not retry) or a
    retry-after in seconds (a temporary rate limit; retry once if time allows).
    capacity: calls each fallback can still take this minute (its rate limit); a full
    fallback is not eligible."""
    budget = RetryBudget(retries, log)
    model = route_model(ticket["route"], routes)
    if model is None:
        log(f"escalate ticket={ticket['id']} reason=no model passes the bar")
        return "escalate"
    err = provider_down.get("primary")
    if err == "quota":
        log("provider 429 quota left=0 -> do not retry; try fallbacks")
    elif err is not None:
        log(f"provider 429 retry-after={err}s")
        if ticket["deadline_left_s"] >= err + MODELS[model]["p95_s"] + RESERVE_S:
            try:
                budget.take("primary", "rate limit")
                ticket = dict(ticket, deadline_left_s=ticket["deadline_left_s"] - err)
                log("primary still 429 after the wait")
            except Exhausted:
                pass
    if err is None:
        log(f"served ticket={ticket['id']} model={model}")
        return model
    for fb in CHAIN:
        ok, why = eligible(fb, ticket, routes)
        if ok and capacity is not None and capacity.get(fb, 0) <= 0:
            ok, why = False, "at capacity"
        if not ok:
            log(f"fallback {fb} {why} -> not allowed")
            continue
        try:
            budget.take(fb, "primary down")
        except Exhausted:
            log(f"escalate {ticket['id']} reason=retry budget spent")
            return "escalate"
        if capacity is not None:
            capacity[fb] -= 1
        log(f"fallback {fb} {why} -> ok")
        log(f"served ticket={ticket['id']} model={fb}")
        return fb
    log(f"escalate {ticket['id']} route={ticket['route']} "
        f"reason=no eligible model")
    return "escalate"


def outage_drill(tickets, capacity, log=lambda s: None):
    """Replay a minute of traffic at the expected failover load against the primary's
    quota outage. Reports where tickets went and the aggregate retries, not one success.
    capacity: fallback calls per minute (example rate limits, simulated)."""
    cap, out, retries = dict(capacity), {}, 0
    for t in tickets:
        lines = []
        where = handle(t, {"primary": "quota"}, lines.append, capacity=cap)
        retries += sum("budget retry" in x for x in lines)
        out[where] = out.get(where, 0) + 1
        for x in lines:
            log(x)
    return out, retries

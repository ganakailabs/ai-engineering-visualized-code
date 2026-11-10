"""Chapter 5: MM-163 Is the Difference Real? An A/B runner with rules set in advance.

The question is SUPERIORITY BY A MARGIN. gain = (resolved share in B) - (in A).
    H0: gain <= MARGIN        H1: gain > MARGIN
MARGIN (0.05) is the smallest gain worth shipping. It is not the gain the plan hopes
for: power is computed at a separate PLANNING ALTERNATIVE above the margin. Plan with
the margin itself and power is about alpha, not 0.8 (the rule ships ~2.5% of the time
when the true gain is exactly the margin).

assign():    sticky by hash of (experiment id, customer): a customer stays in one arm.
             The customer is the randomization unit, so the customer is the analysis
             unit too: each customer counts once, by their FIRST ticket in the test.
planned_n(): customers per arm for the margin test (normal approximation, unpooled
             variance, the same variance the decision's interval uses).
decide():    refuses to call a result before the planned number of matured customers
             per arm; then the two-sided 95% Wald interval for the gain decides:
             lower end above the margin -> ship (a one-sided test at 2.5%).
simulate():  the power check: run the exact decide() rule on many simulated
             experiments and count how often it ships. Independent of the formula.
The outcome is delayed: a ticket counts as resolved only if it was not reopened
within 7 days, so a ticket younger than 7 days has no outcome yet.
"""
import hashlib
import math
import random
from statistics import NormalDist

MATURE_DAYS = 7
Z95 = NormalDist().inv_cdf(0.975)              # 1.96: two-sided 95% = one-sided 2.5%


def assign(exp_id, customer):
    h = int(hashlib.sha256(f"{exp_id}:{customer}".encode()).hexdigest(), 16)
    return "A" if h % 100 < 50 else "B"


def planned_n(base, margin, plan_gain, alpha=0.025, power=0.8):
    """Customers per arm. H0: gain <= margin; H1: gain > margin, one-sided alpha.
    Power is at the planning alternative gain = plan_gain, which must exceed margin."""
    if plan_gain <= margin:
        raise ValueError("plan_gain must be above the margin, or power is about alpha")
    p1, p2 = base, base + plan_gain
    za, zb = NormalDist().inv_cdf(1 - alpha), NormalDist().inv_cdf(power)
    var = p1 * (1 - p1) + p2 * (1 - p2)
    return math.ceil((za + zb) ** 2 * var / (plan_gain - margin) ** 2)


def diff_interval(a_good, a_n, b_good, b_n, z=Z95):
    """Difference B - A and its two-sided 95% Wald interval."""
    pa, pb = a_good / a_n, b_good / b_n
    se = math.sqrt(pa * (1 - pa) / a_n + pb * (1 - pb) / b_n)
    d = pb - pa
    return d, (d - z * se, d + z * se)


def verdict(lo, hi, margin):
    if lo > margin:
        return "ship B: the whole interval is above the margin"
    if hi < margin:
        return "keep A: any gain is smaller than the margin"
    return "inconclusive: the interval straddles the margin"


def decide(arms, planned, margin):
    """arms: {"A": [outcomes], "B": [...]}, one matured outcome per customer."""
    a, b = arms["A"], arms["B"]
    if min(len(a), len(b)) < planned:
        return "not yet", None, None
    d, (lo, hi) = diff_interval(sum(a), len(a), sum(b), len(b))
    return verdict(lo, hi, margin), d, (lo, hi)


def simulate(p_a, p_b, n, margin, reps=2000, seed=11):
    """Share of simulated experiments (n customers per arm, true rates p_a and p_b)
    in which the exact decide() rule ships B."""
    rng = random.Random(seed)
    ships = 0
    for _ in range(reps):
        arms = {"A": [rng.random() < p_a for _ in range(n)],
                "B": [rng.random() < p_b for _ in range(n)]}
        ships += decide(arms, n, margin)[0].startswith("ship")
    return ships / reps


# ---------- the simulated experiment ----------

TRUE = {"A": {"resolved": 0.80, "thumbs_up": 0.70, "escalated": 0.12},   # simulated;
        "B": {"resolved": 0.81, "thumbs_up": 0.72, "escalated": 0.12}}   # only the simulator knows


def traffic(exp_id, days, per_day=240, customers=3000, seed=5):
    """Tickets with their arm and their outcomes. 'resolved' is only knowable
    MATURE_DAYS after the ticket; 'thumbs_up' is known at once."""
    rng = random.Random(seed)
    out = []
    for day in range(1, days + 1):
        for i in range(per_day):
            cust = "asha" if (day in (1, 3, 5) and i == 0) else f"c-{rng.randrange(customers):04d}"
            arm = assign(exp_id, cust)
            p = TRUE[arm]
            out.append({"day": day, "customer": cust, "arm": arm,
                        "thumbs_up": rng.random() < p["thumbs_up"],
                        "resolved": rng.random() < p["resolved"],
                        "escalated": rng.random() < p["escalated"]})
    return out


def first_tickets(tickets):
    """Each customer's first ticket in the experiment: one observation per customer."""
    first = {}
    for t in tickets:
        if t["customer"] not in first:
            first[t["customer"]] = t
    return list(first.values())


def matured(tickets, today, metric="resolved", unit="customer"):
    """Matured outcomes per arm. unit="customer" (the default, and the plan's unit)
    counts each customer once, by their first ticket; unit="ticket" counts every
    ticket, which treats repeat tickets from one customer as independent: wrong for
    a test randomized by customer, kept to show the difference."""
    rows = first_tickets(tickets) if unit == "customer" else tickets
    arms = {"A": [], "B": []}
    for t in rows:
        if today - t["day"] >= MATURE_DAYS:
            arms[t["arm"]].append(t[metric])
    return arms

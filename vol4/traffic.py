"""Chapter 2: a simulated week of tickets (seeded; every number it makes is simulated).

Tuesday has a slow model provider for two hours, so first replies take minutes.
Nothing here is a measurement of a real system.
"""
import random

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
REPLIES = ["Refund of INR {amt} for order #{oid} is on its way (R2).",
           "Order #{oid} is out for delivery; it should reach you tomorrow.",
           "Order #{oid} is final sale, so it cannot be returned (R3)."]


def week(seed=4, per_day=60, slow_day="Tue", slow_tickets=14):
    rng = random.Random(seed)
    tickets = []
    for d, day in enumerate(DAYS):
        for i in range(per_day):
            tenant = "probe" if i % 30 == 0 else rng.choice("aab")      # 2 probes a day
            first_reply_s = round(rng.lognormvariate(2.6, 0.5), 1)       # mostly 5-30 s
            if day == slow_day and i < slow_tickets:
                first_reply_s = round(rng.uniform(90, 400), 1)           # provider incident
            oid = rng.choice(["2001", "1234", "4410"])
            tickets.append({
                "ticket_id": f"T-{d + 1}{i:03d}-{tenant}", "tenant_id": tenant, "day": day,
                "age_days": 7 - d, "first_reply_s": first_reply_s,
                "cancelled": rng.random() < 0.02,
                "reopened": rng.random() < 0.05,
                "tokens": int(rng.uniform(1500, 5200)),
                "reply": rng.choice(REPLIES).format(amt=950, oid=oid)})
    return tickets


# ---------- Chapter 4: two simulated weeks of live replies, by slice ----------

# Slice tags and the clause a correct reply cites (Vol 1 store.py HANDBOOK; series
# scenario catalog: refund SC-001, delivery S1, final sale SC-002, gift card SC-014).
CLAUSE = {"refund": "R2", "delivery": "S1", "final_sale": "R3", "gift_card": "S4"}
SHARE = {"refund": 0.2, "delivery": 0.6, "final_sale": 0.2}
MODEL_UPDATE_DAY = 8          # the provider moves its model alias to a new snapshot


def p_cited(slice_, day):
    """Chance that a reply cites the right clause (simulated; only the simulator knows).
    From day 8 the refund slice slowly loses its citations; the others do not move."""
    base = {"refund": 0.93, "delivery": 0.95, "final_sale": 0.94, "gift_card": 0.8}[slice_]
    if slice_ == "refund" and day >= MODEL_UPDATE_DAY:
        base -= 0.04 * (day - MODEL_UPDATE_DAY + 1)
    return base


def live(days=14, per_day=120, seed=8, extra=None):
    """Replies already sent to customers, one dict per ticket (simulated).
    extra: {slice: (first_day, per_day)} adds a slice that starts later."""
    rng = random.Random(seed)
    out = []
    for day in range(1, days + 1):
        mix = [s for s, w in SHARE.items() for _ in range(int(w * per_day))]
        for s, (first, n) in (extra or {}).items():
            mix += [s] * (n if day >= first else 0)
        for i, s in enumerate(mix):
            ok = rng.random() < p_cited(s, day)
            critical = s == "final_sale" and rng.random() < 0.1    # refund on final sale
            cited = CLAUSE[s] if ok else ("R2" if critical else "none")
            out.append({"ticket_id": f"T-4{day:02d}{i:03d}-a", "day": day, "slice": s,
                        "cited": cited, "expected": CLAUSE[s],
                        "malformed": rng.random() < 0.01,          # grader cannot parse it
                        "model_snapshot": "2026-11" if day >= MODEL_UPDATE_DAY else "2026-10",
                        "reply": f"[{cited}] reply text for {s} (simulated)"})
    return out

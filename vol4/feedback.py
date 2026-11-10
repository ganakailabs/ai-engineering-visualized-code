"""Chapter 5: MM-124 The Feedback Flywheel. Thumbs-down tickets become reviewed cases.

A thumbs-down is a lead, not a label. Code proposes a case from each one (masked
through the Ch 3 sink's redact), review rejects the ones that are not failures (the
reply followed policy and the customer disliked the answer) and the ones already
covered, and a person signs off before a case enters the scenario catalog. Thumbs-
down tickets are not a sample of traffic: they are the tickets someone complained
about, so they find failures but never measure a rate (Chapter 4 measures).
"""
import random

import logsink

TEXT = {"refund": "Asha Rao here, my mug set for order #2001 arrived chipped, refund please. "
                  "Call me on +91 98765 43210.",
        "delivery": "Where is my parcel? Email asha.rao@example.com.",
        "final_sale": "Why can't I return the clearance lamp? I want my money back.",
        "gift_card": "Can I swap my gift card for cash?"}


def thumbs_down(tickets, seed=5):
    """Simulated feedback: wrong replies get more thumbs-down, but so do correct
    denials (a final-sale 'no' is right and still unwelcome)."""
    rng = random.Random(seed)
    out = []
    for t in tickets:
        wrong = t["cited"] != t["expected"]
        p = 0.3 if wrong else 0.12 if t["slice"] == "final_sale" else 0.005
        if rng.random() < p:
            out.append(t)
    return out


def propose(t):
    """A proposed case: masked ticket text, the clause a correct reply cites, what the
    reply did. Raw text never leaves this function."""
    return {"from": t["ticket_id"], "slice": t["slice"], "text": logsink.redact(TEXT[t["slice"]]),
            "expected": t["expected"], "got": t["cited"]}


def review(proposed, catalog, signoff):
    """Returns (approved, rejected with reasons). catalog: signatures already covered.
    signoff(case) is the person; code checks run first."""
    ok, bad, seen = [], [], set(catalog)
    for c in proposed:
        sig = (c["slice"], c["expected"], c["got"])
        if c["got"] == c["expected"]:
            bad.append((c, f"reply was right ({c['expected']})"))
        elif sig in seen:
            bad.append((c, "duplicate of a case already covered"))
        elif not signoff(c):
            bad.append((c, "reviewer declined"))
        else:
            seen.add(sig)
            ok.append(c)
    return ok, bad

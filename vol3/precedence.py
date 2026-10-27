"""When sources disagree: applicability, authority, recency among peers, escalate (Vol 3 Ch 10).

Fictional Northwind clauses. Three dates are kept apart on every clause: published (when
it was written), ingested (when it entered the index) and effective_from (when it starts
to apply). Only effective_from decides applicability. Abstain floors are per source and
chosen on a dev split of scripted retrieval scores; on a real model and scorer they must
be calibrated again ([TO MEASURE] in the book).
"""
from datetime import date

import _root  # noqa: F401

from store import TODAY

AUTHORITY = {"policy": 3, "manual": 2, "past_tickets": 1}
CLAUSES = {
    "R1@2026-06-01": dict(family="R1", source="policy", region="IN", published=date(2026, 5, 20),
                          ingested=date(2026, 5, 21), effective_from=date(2026, 6, 1),
                          text="Returns accepted within 14 days of delivery.", clause="R1.1"),
    "R1@2026-09-15": dict(family="R1", source="policy", region="IN", published=date(2026, 9, 1),
                          ingested=date(2026, 9, 2), effective_from=date(2026, 9, 15),
                          text="Returns accepted within 30 days of delivery.", clause="R1.1"),
    "R1@2026-11-01": dict(family="R1", source="policy", region="IN", published=TODAY,
                          ingested=TODAY, effective_from=date(2026, 11, 1),
                          text="Returns accepted within 21 days of delivery.", clause="R1.1"),
    "R1-EU@2026-01-01": dict(family="R1", source="policy", region="EU", published=date(2025, 12, 1),
                             ingested=date(2025, 12, 2), effective_from=date(2026, 1, 1),
                             text="EU returns accepted within 14 days, by law at minimum.", clause="R1.4"),
    "ticket-8812": dict(family="R1", source="past_tickets", region="IN", published=date(2026, 10, 3),
                        ingested=date(2026, 10, 3), effective_from=date(2026, 10, 3),
                        text="Agent: returns are 7 days only now.", clause="msg 4"),
    "M7@2026-08-01a": dict(family="M7", source="manual", region="IN", published=date(2026, 7, 20),
                           ingested=date(2026, 7, 21), effective_from=date(2026, 8, 1),
                           text="NW-500 battery: replace after 300 cycles.", clause="4.2"),
    "M7@2026-08-01b": dict(family="M7", source="manual", region="IN", published=date(2026, 7, 22),
                           ingested=date(2026, 7, 23), effective_from=date(2026, 8, 1),
                           text="NW-500 battery: replace after 500 cycles.", clause="4.2"),
}


def precedence(ids, region="IN", today=TODAY):
    """Returns (kept ids, [(dropped id, reason)], escalate?)."""
    dropped, live = [], []
    for i in ids:                                            # 1 applicability
        c = CLAUSES[i]
        if c["region"] != region:
            dropped.append((i, "not applicable region"))
        elif c["effective_from"] > today:
            dropped.append((i, "not yet effective"))
        else:
            live.append(i)
    families = {}
    for i in live:
        families.setdefault(CLAUSES[i]["family"], []).append(i)
    kept, escalate = [], False
    for fam in families.values():
        top = max(AUTHORITY[CLAUSES[i]["source"]] for i in fam)  # 2 authority
        for i in fam:
            if AUTHORITY[CLAUSES[i]["source"]] < top:
                dropped.append((i, "authority"))
        peers = [i for i in fam if AUTHORITY[CLAUSES[i]["source"]] == top]
        newest = max(CLAUSES[i]["effective_from"] for i in peers)  # 3 recency among peers
        for i in peers:
            if CLAUSES[i]["effective_from"] < newest:
                dropped.append((i, "superseded"))
        last = [i for i in peers if CLAUSES[i]["effective_from"] == newest]
        if len({CLAUSES[i]["text"] for i in last}) > 1:          # 4 escalate
            escalate = True
        else:
            kept.append(last[0])
    return kept, dropped, escalate


def cite(i):
    c = CLAUSES[i]
    return f"[{c['source']} {i} clause {c['clause']}, effective {c['effective_from']}]"


# Scripted retrieval scores with whether the passage answered the question (dev / held-out).
SCORES = {
    "policy": {"dev": [(.82, 1), (.74, 1), (.61, 1), (.48, 0), (.40, 0)],
               "held": [(.79, 1), (.66, 1), (.52, 0), (.44, 0)]},
    "manual": {"dev": [(.77, 1), (.69, 1), (.58, 0), (.55, 1), (.37, 0)],
               "held": [(.71, 1), (.57, 1), (.49, 0), (.35, 0)]},
    "past_tickets": {"dev": [(.88, 1), (.81, 0), (.76, 0), (.71, 1), (.62, 0)],
                     "held": [(.86, 1), (.79, 0), (.70, 0), (.64, 0)]},
}
FLOORS = [round(x * 0.05, 2) for x in range(6, 19)]           # 0.30 .. 0.90


def outcome(rows, floor):
    """Right = answered and correct, or abstained and wrong."""
    return sum((s >= floor) == bool(ok) for s, ok in rows), len(rows)


def calibrate(source):
    rows = SCORES[source]["dev"]
    return max(FLOORS, key=lambda f: (outcome(rows, f)[0], f))   # ties: the stricter floor


def abstain(source, score, floors):
    return score < floors[source]

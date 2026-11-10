"""Chapter 4: online evaluation. Score a sample of live replies, then watch for drift.

MM-122 Shadow Evaluation: copy a recorded, stratified sample of replies that were
       already sent, and grade the copies off the reply path. Nothing the customer
       sees waits for, or is changed by, the grader. Failed gradings are counted, and
       every score carries the grader version that produced it.
       (This is SHADOW SCORING. The other workflow, a SHADOW RUN, sends copies of live
       inputs to a candidate and grades outputs nobody is served; see the docs.)
MM-123 Drift Watch: a trend per slice, with an interval, compared with a baseline.
       One bad day is noise; a recent window whose whole interval sits below the
       baseline's interval is an alert. That rule is the lab's alert HEURISTIC over
       overlapping windows, not a calibrated test with a known false-alert rate.
       Critical rules are checked on every reply, not sampled.

The traffic is simulated (traffic.live). The graders are code: v1 checks that the
reply cites the clause its slice needs; v2 is a scripted stand-in for a new grader
(a model judge in real life) that disagrees with people on refund cases.
"""
import hashlib
import json
import math
import random

GRADER = "v1"                  # pinned: a score is only comparable with its own grader
AGREE_FLOOR = 0.90             # lab choice: a new grader must agree this often with people
COVERAGE_FLOOR = 0.95          # lab choice: share of a slice's sample that must be graded
Z95 = 1.96


def plan(strata, rate=0.25, min_per_stratum=8, seed=4, version=1):
    """The sample plan is data, recorded next to the scores it produced."""
    return {"version": version, "strata": list(strata), "rate": rate,
            "min_per_stratum": min_per_stratum, "seed": seed}


def sample(tickets, p, day):
    """Stratified sample of one day's replies. Returns (sample, unplanned): copies of
    the sampled tickets, and the slices that have no stratum in the plan."""
    rng = random.Random(f"{p['seed']}-{day}")
    picked, unplanned = [], sorted({t["slice"] for t in tickets} - set(p["strata"]))
    for s in p["strata"]:
        pool = [t for t in tickets if t["slice"] == s]
        n = min(len(pool), max(p["min_per_stratum"], round(p["rate"] * len(pool))))
        picked += [dict(t, weight=len(pool) / n) for t in rng.sample(pool, n)]
    return picked, unplanned


def grade(t, version=GRADER):
    """One grading: True, False or None (failed). v1 is the code check."""
    if t["malformed"]:
        return None
    if version == "v1":
        return t["cited"] == t["expected"]
    # v2 (scripted): stricter on refunds, and wrong about it on some of them
    h = int(hashlib.sha256(t["ticket_id"].encode()).hexdigest(), 16)
    return t["cited"] == t["expected"] and not (t["slice"] == "refund" and h % 3 == 0)


def wilson(good, n, z=Z95):
    """95% Wilson score interval for a proportion; (0, 1) when n is 0."""
    if n == 0:
        return 0.0, 1.0
    p = good / n
    mid = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, mid - half), min(1.0, mid + half)


def score(graded, slice_=None):
    """graded: [(ticket, result)]. Failed gradings are counted, not dropped."""
    rows = [(t, r) for t, r in graded if slice_ in (None, t["slice"])]
    done = [r for _, r in rows if r is not None]
    good = sum(done)
    lo, hi = wilson(good, len(done))
    return {"n": len(done), "good": good, "failed": len(rows) - len(done),
            "rate": good / len(done) if done else None, "lo": lo, "hi": hi}


def coverage(graded, strata, floor=COVERAGE_FLOOR):
    """Publication gate per slice: graded / sampled. A grader that fails mostly on
    hard cases makes the slice look better; below the floor, the slice's rate is
    withheld instead of published. Returns {slice: (coverage, publish?)}."""
    out = {}
    for s in strata:
        rows = [r for t, r in graded if t["slice"] == s]
        cov = sum(r is not None for r in rows) / len(rows) if rows else 0.0
        out[s] = (cov, cov >= floor)
    return out


def weighted_overall(graded):
    """The all-traffic rate, reweighted by the plan (refund is 20% of traffic, not of
    the sample). This is the number a single dashboard tile would show."""
    w = [(t["weight"], r) for t, r in graded if r is not None]
    return sum(wt for wt, r in w if r) / sum(wt for wt, _ in w)


def recheck(candidate, human_labels):
    """Before a new grader's scores are used: agreement with people on labelled cases."""
    agree = sum(grade(t, candidate) == label for t, label in human_labels)
    return agree, len(human_labels), agree / len(human_labels) >= AGREE_FLOOR


def drift(daily, baseline_days, recent_days):
    """daily: {day: [(ticket, result)]} for ONE slice. Pool the baseline and the recent
    window; alert only when the two intervals do not touch (recent high < baseline low)."""
    base = score([g for d in baseline_days for g in daily.get(d, [])])
    recent = score([g for d in recent_days for g in daily.get(d, [])])
    if base["n"] == 0:
        return {"base": None, "recent": recent, "alert": "new slice, no baseline"}
    down = recent["n"] > 0 and recent["hi"] < base["lo"]
    return {"base": base, "recent": recent, "alert": "trend=down alert" if down else None}


def critical(tickets):
    """Code rule on EVERY reply, not a sample: no refund cited on a final-sale ticket."""
    return [t["ticket_id"] for t in tickets if t["slice"] == "final_sale" and t["cited"] == "R2"]


def fingerprint(tickets):
    """Hash of the sent replies: the shadow scorer must leave it unchanged."""
    return hashlib.sha256(json.dumps([t["reply"] for t in tickets]).encode()).hexdigest()

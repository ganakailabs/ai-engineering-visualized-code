"""Chapter 6: Release Engineering: Versioning, CI and Rollbacks.

Run from the repo root:  python3 vol4/ch06.py
Part 1 checks release 15's manifest and runs CI (Vol 3's gate on the scenario
catalog, scripted case results). Part 2 resumes a job that started on release 14,
first from an unversioned checkpoint, then pinned and migrated. Part 3 sends 10% of
customers to release 15, compares the refund slice with the Ch 5 interval, and rolls
back after a deletion. Canary traffic and its scores are simulated.
"""
import random

import _root  # noqa: F401

import experiment as E
import release as R

CANARY_SHARE = 10


def canary(seed=6, days=3, per_day=480):
    """Refund tickets on 14 and on 15, graded off the reply path (simulated rates)."""
    rng = random.Random(seed)
    p = {"rel-14": 0.93, "rel-15": 0.70}         # chance a refund reply cites R2 (simulated)
    arms, sent_on_15 = {"rel-14": [], "rel-15": []}, []
    for day in range(1, days + 1):
        for i in range(per_day):
            cust = f"c-{rng.randrange(3000):04d}"
            rel = "rel-15" if R.in_canary(cust, "rel-15", CANARY_SHARE) else "rel-14"
            is_refund = rng.random() < 0.2
            cited = rng.random() < p[rel]
            if is_refund:
                arms[rel].append(cited)
                if rel == "rel-15" and cited:
                    sent_on_15.append(f"T-6{day}{i:03d}-a")
    return arms, sent_on_15


def deletion_after_release():
    """Release 15 ships; then asha withdraws consent (SC-020) and two memories go."""
    dep = R.Deploy("rel-14", {"mem-asha-1": "episode", "mem-asha-2": "episode",
                              "mem-c-0042-1": "episode"})
    dep.ship("rel-15")
    dep.delete(["mem-asha-1", "mem-asha-2"])
    return dep


if __name__ == "__main__":
    print("== Part 1: the manifest and CI ==")
    m14, m15 = R.load("rel-14"), R.load("rel-15")
    v = m14["versions"]
    pairs = [f"{k}={v[k]}" for k in R.VERSIONS]
    print("release rel-14: " + " ".join(pairs[:5]))
    print("  " + " ".join(pairs[5:]))
    print(f"manifest rel-15 check: {R.check(m15) or 'complete'}")
    g = R.ci("prompt v7", "prompt v8")
    print(f"ci prompt v8: critical cases failed={len(g['critical'])} "
          f"({', '.join(g['critical'])}) -> merge {g['verdict']}")
    g = R.ci("prompt v7", "prompt v8.1")
    print("ci prompt v8.1: critical cases failed=0")
    print(f"  -> {g['label']}")
    m15["versions"]["prompt"], m15["eval_report"] = "v8.1", {"gate": g["label"]}
    print(f"manifest rel-15 check: {R.check(m15) or 'complete'}")

    print("\n== Part 2: an in-flight job across the release (MM-140) ==")
    ck = R.checkpoint("rel-14", "v2", {"refund-2001"})
    unversioned = {k: v for k, v in ck.items() if k not in ("schema", "release_id")}
    payments = ["refund-2001"]                    # sent on Friday, under release 14
    seen = R.resume(unversioned, "v3", payments)
    print("naive  job=op-a-T-2001-a unversioned checkpoint read by rel-15 (v3):")
    print(f"  done={sorted(seen)} -> payments={len(payments)}")
    payments = ["refund-2001"]
    pinned = {"rel-14": m14, "rel-15": m15}[ck["release_id"]]   # the job's own release
    R.resume(ck, pinned["versions"]["checkpoint"], payments)
    print(f"job=op-a-T-2001-a pinned release={pinned['release_id'][4:]} -> finished on "
          f"{pinned['release_id'][4:]} payments={len(payments)}")
    payments = ["refund-2001"]
    R.resume(R.migrate_v2_v3(ck), "v3", payments)
    print(f"or: migrate checkpoint v2 -> v3, resume on 15 -> payments={len(payments)}")

    print("release matrix (rel-15 live; issue_refund revoked on Monday):")
    jobs = (("new", {"release": "rel-15", "effects": False, "next_op": "reply"}),
            ("old, no effects", {"release": "rel-14", "effects": False,
                                         "next_op": "issue_refund"}),
            ("old, effects, next=notify", {"release": "rel-14", "effects": True,
                                               "next_op": "notify"}),
            ("old, effects, next=refund", {"release": "rel-14", "effects": True,
                                               "next_op": "issue_refund"}))
    for label, job in jobs:
        print(f"  {label:<26}-> {R.route_job(job, 'rel-15', {'issue_refund'})}")

    print("\n== Part 3: canary and rollback (MM-141) ==")
    arms, sent = canary()
    a, b = arms["rel-14"], arms["rel-15"]
    d, (lo, hi) = E.diff_interval(sum(a), len(a), sum(b), len(b))
    print(f"canary release=15 share={CANARY_SHARE}% (sticky by customer), 3 days, refund slice")
    print(f"  policy_cited rel-14={sum(a)}/{len(a)} rel-15={sum(b)}/{len(b)}")
    print(f"  diff={d:+.3f} [{lo:+.3f},{hi:+.3f}] -> "
          f"{'rollback' if hi < 0 else 'continue'}")
    naive, dep = deletion_after_release(), deletion_after_release()
    naive.rollback_naive("rel-14")
    print(f"naive  restore rel-14 snapshot -> deleted ids back="
          f"{sum(i in naive.data for i in naive.deleted)}")
    kept = dep.rollback("rel-14")
    print(f"rollback release=15 -> 14 deleted_ids kept deleted={kept} live={dep.live}")
    print(f"refunds sent on 15={len(sent)} cannot be unsent -> listed for review")
    print("  (compensation is a new action)")
    rng = random.Random(7)
    acted = sum(rng.random() < 0.4 for _ in range(12))     # simulated
    print(f"in flight on 15: 12 jobs: {12 - acted} no action yet -> restart on 14;")
    print(f"  {acted} acted -> finish on 15, flagged for review")

"""Chapter 4: Online Evaluation: Shadow Scoring and Drift.

Run from the repo root:  python3 vol4/ch04.py
Two simulated weeks of replies that were already sent (traffic.live). A recorded,
stratified sample is copied and graded off the reply path; the sent replies are
hashed before and after to show that nothing changed. On day 8 the provider moves
its model alias to a new snapshot and the refund slice starts losing citations
(simulated). The overall average stays above its floor; the per-slice drift watch
does not. A new grader is checked against people before its scores are used.
"""
import random

import _root  # noqa: F401

import shadow as S
import traffic

FLOOR = 0.85                                   # the naive dashboard's overall floor
BASELINE, WATCH = range(1, 8), range(8, 15)


def run(tickets, plan, grader=S.GRADER):
    """Sample and grade every day. Returns ({slice: {day: [(t, result)]}}, totals)."""
    daily, tot = {}, {"seen": 0, "sampled": 0, "failed": 0, "unplanned": set()}
    for day in sorted({t["day"] for t in tickets}):
        today = [t for t in tickets if t["day"] == day]
        picked, unplanned = S.sample(today, plan, day)
        tot["seen"] += len(today)
        tot["sampled"] += len(picked)
        tot["unplanned"] |= set(unplanned)
        for t in picked:
            r = S.grade(t, grader)
            tot["failed"] += r is None
            daily.setdefault(t["slice"], {}).setdefault(day, []).append((t, r))
    return daily, tot


def naive_dashboard(tickets, rate=0.1, seed=1):
    """One tile: overall pass rate of a uniform 10% sample, per week."""
    rng = random.Random(seed)
    out = []
    for week in (BASELINE, WATCH):
        got = [S.grade(t) for t in tickets if t["day"] in week and rng.random() < rate]
        got = [g for g in got if g is not None]
        out.append(sum(got) / len(got))
    return out


def first_alert(per_day, window=3):
    for end in WATCH:
        d = S.drift(per_day, BASELINE, range(end - window + 1, end + 1))
        if d["alert"]:
            return end, d, f"{end - window + 1}-{end}"
    end = WATCH[-1]
    return None, S.drift(per_day, BASELINE, range(end - window + 1, end + 1)), \
        f"{end - window + 1}-{end}"


def fmt(s):
    return f"{s['rate']:.2f} [{s['lo']:.2f},{s['hi']:.2f}] n={s['n']}"


if __name__ == "__main__":
    tickets = traffic.live()
    print("== Part 1: shadow scoring (MM-122) ==")
    plan = S.plan(["refund", "delivery", "final_sale"])
    print(f"plan v{plan['version']} strata={','.join(plan['strata'])} rate={plan['rate']} "
          f"min={plan['min_per_stratum']} seed={plan['seed']} grader={S.GRADER}")
    before = S.fingerprint(tickets)
    daily, tot = run(tickets, plan)
    print(f"14 days: replies={tot['seen']} sampled={tot['sampled']} "
          f"grading failed={tot['failed']} (counted)")
    print(f"replies changed={0 if S.fingerprint(tickets) == before else 'YES'} "
          f"(hash of sent replies before == after)")
    graded = [g for s in daily.values() for d in s.values() for g in d]
    cov = S.coverage(graded, plan["strata"])
    print("grading coverage " + " ".join(f"{s}={c:.2f}" for s, (c, _) in cov.items()))
    print(f"  floor={S.COVERAGE_FLOOR} -> "
          + ("publish" if all(ok for _, ok in cov.values()) else "withhold"))
    # 40 week-1 replies that people labelled (the labels here are the simulator's truth)
    labelled = [g for day in BASELINE for s in ("refund", "delivery")
                for g in daily[s][day][:3] if g[1] is not None][:40]
    agree, n, ok = S.recheck("v2", [(t, t["cited"] == t["expected"]) for t, _ in labelled])
    print(f"grader version changed v1 -> v2 (day 9) -> recheck vs human labels")
    print(f"  agree={agree}/{n} ({agree / n:.2f}) floor={S.AGREE_FLOOR} "
          f"-> {'switch to v2' if ok else 'keep v1 pinned'}")
    crit = S.critical(tickets)
    print(f"critical rule on every reply: refund cited on final sale={len(crit)} "
          f"{crit} -> alert at once")

    print("\n== Part 2: the silent drop (naive dashboard) ==")
    w1, w2 = naive_dashboard(tickets)
    print(f"overall week 1={w1:.2f} week 2={w2:.2f} floor={FLOOR} -> "
          f"{'alert' if w2 < FLOOR else 'no alert'}")

    print("\n== Part 3: drift watch per slice (MM-123) ==")
    print("baseline days 1-7; 3-day window from day 8;")
    print("  alert when the intervals do not touch")
    for s in plan["strata"]:
        day, d, days = first_alert(daily[s])
        tail = "trend=down alert" if day else "ok"
        print(f"drift policy_cited slice={s} base={fmt(d['base'])}")
        print(f"  days {days}={fmt(d['recent'])} {tail}")
    changed = sorted({(t["day"], t["model_snapshot"]) for t in tickets}, key=lambda x: x[0])
    snaps = []
    for day, snap in changed:
        if not snaps or snaps[-1][1] != snap:
            snaps.append((day, snap))
    print("change log: " + ", ".join(f"day {d} model snapshot {s}" for d, s in snaps))

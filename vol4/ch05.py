"""Chapter 5: Feedback and Experiments.

Run from the repo root:  python3 vol4/ch05.py
Part 1 turns two weeks of thumbs-down tickets (Chapter 4's simulated traffic) into
reviewed cases, and splits the approved ones with Vol 3's hash split. Part 2 starts
an A/B test of prompt v8 (B) against v7 (A): sticky assignment by customer, a
superiority-by-margin plan written before the run (null, alternative, margin,
planning alternative, alpha, power), a power check of the exact decision rule by
simulation, and a delayed outcome. After one morning, the naive call crowns a winner
on thumbs-up; the runner says not yet. All numbers are simulated.
"""
import textwrap
import _root  # noqa: F401

import experiment as E
import feedback as F
import gate                                   # Vol 3 Ch 16: the stable dev/held-out split
import traffic

EXP, BASE = "exp-v8", 0.80          # set before the run, written down
MARGIN = 0.05                       # smallest gain worth shipping (H0: gain <= MARGIN)
PLAN_GAIN = 0.10                    # planning alternative: the gain the team hopes for
ALPHA, POWER = 0.025, 0.80          # one-sided alpha (= lower end of a 95% interval)
CATALOG = {("final_sale", "R3", "R2")}          # SC-002 already covers refund-on-final-sale


def flywheel(tickets, signoff=lambda case: True):
    down = F.thumbs_down(tickets)
    proposed = [F.propose(t) for t in down]
    approved, rejected = F.review(proposed, CATALOG, signoff)
    return down, proposed, approved, rejected


def morning(tickets, n=60):
    """The naive call: first 60 tickets per arm on day 1, thumbs-up, biggest wins."""
    arms = {"A": [], "B": []}
    for t in tickets:
        if t["day"] == 1 and len(arms[t["arm"]]) < n:
            arms[t["arm"]].append(t["thumbs_up"])
    return arms


if __name__ == "__main__":
    print("== Part 1: the feedback flywheel (MM-124) ==")
    down, proposed, approved, rejected = flywheel(traffic.live())
    print(f"feedback thumbs_down={len(down)} proposed={len(proposed)} approved={len(approved)}")
    reasons = {}
    for _, why in rejected:
        reasons[why] = reasons.get(why, 0) + 1
    for why, n in sorted(reasons.items()):
        print(f"  rejected {n}: {why}")
    case = approved[0]
    print(f"  case from {case['from']}:")
    for part in textwrap.wrap(f"\"{case['text']}\"", 70):
        print("    " + part)
    print(f"    expected={case['expected']} got={case['got']}")
    dev, held = gate.split([(c["expected"], c["from"] + " " + c["text"], c["expected"])
                            for c in approved])
    print(f"  split dev={len(dev)} held_out={len(held)} (Vol 3 hash split)")

    print("\n== Part 2: is the difference real? (MM-163) ==")
    planned = E.planned_n(BASE, MARGIN, PLAN_GAIN, ALPHA, POWER)
    print(f"plan {EXP}: unit=customer, outcome=first ticket resolved, "
          f"no reopen in {E.MATURE_DAYS} days")
    print(f"  H0: gain <= {MARGIN}  H1: gain > {MARGIN}  (gain = B - A)")
    print(f"  base={BASE:.2f} margin={MARGIN:.2f} plan_gain={PLAN_GAIN:.2f} "
          f"alpha={ALPHA} one-sided power={POWER:.2f}")
    print(f"  -> n={planned} customers per arm")
    reps = 2000
    hit = E.simulate(BASE, BASE + PLAN_GAIN, planned, MARGIN, reps)
    edge = E.simulate(BASE, BASE + MARGIN, planned, MARGIN, reps, seed=12)
    print(f"power check: the exact rule on {reps} simulated tests of {planned} per arm")
    print(f"  true gain {PLAN_GAIN:.2f} -> ships {hit:.3f} (power)")
    print(f"  true gain {MARGIN:.2f} -> ships {edge:.3f} (false ship, alpha)")
    tickets = E.traffic(EXP, days=1)
    week = E.traffic(EXP, days=5)
    asha = [t["arm"] for t in week if t["customer"] == "asha"]
    counted = sum(t["customer"] == "asha" for t in E.first_tickets(week))
    print(f"assign customer=asha arm={','.join(sorted(set(asha)))} tickets={len(asha)} "
          f"counted={counted}")
    print("  (sticky; one customer, one outcome)")
    print("naive: first 60 tickets per arm, thumbs-up, five seeded mornings,")
    print("  same true rates")
    for seed in range(5, 10):
        m = morning(E.traffic(EXP, days=1, seed=seed))
        a, b = sum(m["A"]), sum(m["B"])
        d, (lo, hi) = E.diff_interval(a, len(m["A"]), b, len(m["B"]))
        call = "B wins" if b > a else "A wins" if a > b else "tie"
        print(f"  morning seed={seed} A={a}/60 B={b}/60 -> {call:<6} "
              f"(diff={d:+.3f} [{lo:+.3f},{hi:+.3f}])")
    arms = E.matured(tickets, today=1)
    verdict, _, _ = E.decide(arms, planned, MARGIN)
    print(f"ab outcome=resolved matured customers A={len(arms['A'])} B={len(arms['B'])} "
          f"of {planned} -> {verdict}")

"""Implementation test for Chapter 5: sticky arms, customer units, no early call, the
margin plan, an exact power check of the decision rule, reviewed cases only."""
import _path  # noqa: F401

import math

import ch05
import experiment as E
import traffic

tickets = E.traffic(ch05.EXP, days=10)
arms = {}
for t in tickets:
    arms.setdefault(t["customer"], set()).add(t["arm"])
assert all(len(a) == 1 for a in arms.values())                 # a customer never switches
planned = E.planned_n(ch05.BASE, ch05.MARGIN, ch05.PLAN_GAIN, ch05.ALPHA, ch05.POWER)
assert planned == 785
try:
    E.planned_n(ch05.BASE, ch05.MARGIN, ch05.MARGIN)            # planning at the margin
    raise AssertionError("planning at the margin must be refused")
except ValueError:
    pass
assert E.decide({"A": [True] * (planned - 1), "B": [True] * planned},
                planned, ch05.MARGIN)[0] == "not yet"
assert E.matured(tickets, today=7) == {"A": [], "B": []}        # nothing is 7 days old yet
# customer units: Asha's three tickets are one observation
assert sum(t["customer"] == "asha" for t in E.first_tickets(E.traffic(ch05.EXP, days=5))) == 1
by_c, by_t = E.matured(tickets, today=10), E.matured(tickets, today=10, unit="ticket")
assert sum(map(len, by_c.values())) == len({t["customer"] for t in E.first_tickets(tickets)
                                            if 10 - t["day"] >= 7})
assert sum(map(len, by_t.values())) > sum(map(len, by_c.values()))

# Independent check of power and alpha for the EXACT rule, by exact enumeration over
# the two binomial distributions (no simulation, no sample-size formula). The interval
# is re-implemented here rather than imported.


def pmf(n, p):
    lg = math.lgamma
    return [math.exp(lg(n + 1) - lg(k + 1) - lg(n - k + 1) + k * math.log(p)
                     + (n - k) * math.log(1 - p)) for k in range(n + 1)]


def p_ship(pa, pb, n, margin, z=1.959963984540054):
    A, B, tot = pmf(n, pa), pmf(n, pb), 0.0
    for a, wa in enumerate(A):
        if wa < 1e-15:
            continue
        for b, wb in enumerate(B):
            if wb < 1e-15:
                continue
            qa, qb = a / n, b / n
            lo = (qb - qa) - z * math.sqrt((qa * (1 - qa) + qb * (1 - qb)) / n)
            tot += wa * wb * (lo > margin)
    return tot


power = p_ship(0.80, 0.90, planned, ch05.MARGIN)
alpha = p_ship(0.80, 0.85, planned, ch05.MARGIN)
assert 0.80 <= power < 0.81, power                              # 0.8016
assert 0.024 < alpha <= 0.0251, alpha                           # 0.0250
assert abs(E.simulate(0.80, 0.90, planned, ch05.MARGIN, 2000) - power) < 0.03

# the worked example in the chapter text
d, (lo, hi) = E.diff_interval(640, 800, 712, 800)
assert (round(d * 100, 1), round(lo * 100, 1), round(hi * 100, 1)) == (9.0, 5.5, 12.5)
assert E.verdict(lo, hi, ch05.MARGIN).startswith("ship")

down, proposed, approved, rejected = ch05.flywheel(traffic.live())
assert all(c["got"] != c["expected"] for c in approved)
assert not any("Asha" in c["text"] or "+91" in c["text"] for c in proposed)
_, _, none, _ = ch05.flywheel(traffic.live(), signoff=lambda c: False)
assert none == []                                               # no sign-off, no case
print(f"test_experiment: OK (exact power={power:.4f} alpha={alpha:.4f} at n={planned})")

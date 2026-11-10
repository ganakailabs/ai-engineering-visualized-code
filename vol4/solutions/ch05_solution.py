"""Chapter 5 exercise: Stop the early call.

Run the A/B test of prompt v8 for one simulated day, then until both arms have the
planned number of matured CUSTOMERS. Predict first: does the answer change, and does
v8 clear the margin?

The plan was written before the run: H0 gain <= 0.05, H1 gain > 0.05, planning
alternative 0.10, one-sided alpha 0.025, power 0.8, so 785 customers per arm. Each
customer counts once, by their first ticket. decide() refuses to answer before that.
Tickets keep arriving at 240 a day (simulated); an outcome matures 7 days later.
Then the same rule is run on traffic from only 41 customers (40 plus Asha): thousands of tickets,
but too few independent units to call anything.
"""
import _path  # noqa: F401

import ch05
import experiment as E

planned = E.planned_n(ch05.BASE, ch05.MARGIN, ch05.PLAN_GAIN, ch05.ALPHA, ch05.POWER)
tickets = E.traffic(ch05.EXP, days=40)
verdict, _, _ = E.decide(E.matured(tickets, today=1), planned, ch05.MARGIN)
print(f"day 1: {verdict}")
assert verdict == "not yet"

for today in range(2, 41):
    arms = E.matured(tickets, today)
    verdict, d, interval = E.decide(arms, planned, ch05.MARGIN)
    if d is not None:
        break
    assert min(len(arms["A"]), len(arms["B"])) < planned       # no call before the size
lo, hi = interval
print(f"day {today}: matured customers A={len(arms['A'])} B={len(arms['B'])} "
      f"(planned {planned})")
print(f"ab gain={d:+.3f} interval=[{lo:+.3f},{hi:+.3f}] margin={ch05.MARGIN}")
print(f"  -> {verdict}")
esc = {arm: sum(t["escalated"] for t in tickets if t["arm"] == arm and today - t["day"] >= 7)
       for arm in "AB"}
print(f"escalations A={esc['A']} B={esc['B']} (workload, all matured tickets, simulated)")
assert hi < ch05.MARGIN and verdict.startswith("keep A")    # the rule held

few = E.traffic(ch05.EXP, days=40, customers=40, seed=6)
by_ticket = E.matured(few, today=40, unit="ticket")
by_customer = E.matured(few, today=40)
v_few = E.decide(by_customer, planned, ch05.MARGIN)[0]
n_cust = len({t["customer"] for t in few})
print(f"{n_cust} customers: tickets A={len(by_ticket['A'])} B={len(by_ticket['B'])}, "
      f"customers A={len(by_customer['A'])} B={len(by_customer['B'])} -> {v_few}")
assert min(len(v) for v in by_ticket.values()) >= planned and v_few == "not yet"
print("ch05 solution: OK")

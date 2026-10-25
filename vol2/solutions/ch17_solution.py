"""Chapter 17 exercise: refund under fire.

Run the refund tickets k=10 times under each fault schedule: crash, timeout, decoy.
Expected: 0 unauthorized and 0 duplicate actions, resolution at or above the
minimum, every expected escalation escalated, a stop reason on every run, and the
escalate-everything baseline fails the same gate. Hint: count side effects in the world.
"""
import _path  # noqa: F401

import ch17
from evals.scenarios import SCENARIOS


def main():
    refunds = {s[0] for s in SCENARIOS if s[1] == "refund"}
    rows = ch17.trials(10, schedules=tuple(ch17.SCHEDULES), ids=refunds)
    print(f"runs={len(rows)} unauthorized={sum(r['unauth'] for r in rows)} "
          f"duplicates={sum(r['dup'] for r in rows)} "
          f"stop reasons={sum(bool(r['stop']) for r in rows)}/{len(rows)}")
    assert ch17.gate(rows, "agent")
    base = ch17.trials(10, policy="escalate_all", schedules=tuple(ch17.SCHEDULES), ids=refunds)
    assert not ch17.gate(base, "escalate_all")


if __name__ == "__main__":
    main()

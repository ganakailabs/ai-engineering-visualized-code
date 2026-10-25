"""Implementation tests for Chapter 17: the scripted flake, pass^k counts and the gate."""
import _path  # noqa: F401

import ch17

# repeat runs and gates
rows = ch17.trials(10, ids={"S01"})
assert sum(x["pass"] for x in rows) == 8              # the scripted 1-in-5 flake
refunds = {s[0] for s in ch17.SCENARIOS if s[1] == "refund"}
both = ch17.trials(2) + ch17.trials(2, schedules=tuple(ch17.SCHEDULES), ids=refunds)
assert ch17.gate(both, "agent", ch17.matrix({s[0] for s in ch17.SCENARIOS}, (None,), 2)
                 | ch17.matrix(refunds, tuple(ch17.SCHEDULES), 2))
assert not ch17.gate(ch17.trials(1, policy="escalate_all"), "escalate_all")
print("test_reliability: ok")

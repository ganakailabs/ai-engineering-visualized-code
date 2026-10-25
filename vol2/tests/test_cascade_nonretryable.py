"""Ch15 audit: a non-retryable error must not consume the shared retry budget."""
import _path  # noqa: F401

import cascade
from world import WorldError

calls, log = [], []
budget = cascade.RetryBudget(5, log.append)


def invalid():
    calls.append(1)
    raise WorldError("INVALID_ARGUMENT", transient=False)


try:
    cascade.nested(invalid, lambda layer: budget, "payments")
    raise AssertionError("must raise")
except WorldError as e:
    assert e.code == "INVALID_ARGUMENT"
assert (len(calls), budget.left) == (1, 5), (len(calls), budget.left, log)
print("ok non-retryable error: 1 call, budget untouched")

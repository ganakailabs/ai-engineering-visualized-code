"""Implementation tests for Chapter 8: the stream contract, resume, cancel, flood."""
import _path  # noqa: F401

import stream as S

# no decision text before the checked final, for every order; naive leaks it for some
for oid in ("1234", "2001", "3100", "4410"):
    s, ok, clause = S.contract_stream(oid)
    assert not S.decision_before_final(s), oid
    final = next(e for e in s.events if e["event"] == "final")["data"]
    assert ok or "approved" not in final, oid
naive, ok, clause = S.naive_stream("3100")
assert S.decision_before_final(naive) and not ok and clause == "R4"
naive, ok, clause = S.naive_stream("4410")
assert not ok and clause == "R3"
assert S.contract_stream("2001")[1]          # damaged, 3 days: the refund may go out

# resume after reconnect: no gap, no repeat
s, _, _ = S.contract_stream("3100")
for last in range(0, len(s.events) + 1):
    seen = [e["id"] for e in s.events[:last]] + [e["id"] for e in s.since(last)]
    assert seen == list(range(1, len(s.events) + 1))
assert S.sse({"id": 2, "event": "working", "data": "x"}) == "id: 2\nevent: working\ndata: x\n\n"

# cancel stops at a safe state: never between pay and record
for step in S.STEPS:
    ran = S.run_with_cancel(step)
    assert not (ran[-1] == "pay"), step
assert S.run_with_cancel("decide") == ["lookup", "decide"]

# sizing and flood
assert S.workers_needed(30, 12, 0.75) == (6.0, 8)
assert S.queue_limit(8, 12, 60) == 32
for rate in (30, 60, 90, 300):
    out, done = S.simulate(rate, 5, 8, 12, 60)
    adm = [t for t, o in out.items() if o["admitted"]]
    assert sorted(done) == sorted(adm)                      # none lost, none twice
    assert all(out[t]["reply_s"] <= 60 for t in adm)
out, _ = S.simulate(30, 10, 8, 12, 60)
assert all(o["admitted"] for o in out.values())             # the peak itself fits
# sensitive non-decision output: a delivery draft naming another customer's address
# is held for the check and never streamed early; a clean delivery update passes
leak = "Your order #2001 goes to " + S.ADDRESSES["c-42"] + " tomorrow."
d, ok, clause = S.delivery_stream("2001", leak)
assert (ok, clause) == (False, "privacy")
assert all(S.ADDRESSES["c-42"] not in e["data"] for e in d.events)
assert not S.decision_before_final(d)
d2, ok2, _ = S.delivery_stream("2001", "Your order #2001 arrives tomorrow.")
assert ok2 and d2.events[-2]["data"] == "Your order #2001 arrives tomorrow."
# the owner's own address is not a leak
assert S.check_output("2001", "Delivering to " + S.ADDRESSES["asha"] + ".")[0]
# a long tail breaks a limit sized on the mean
out, _ = S.simulate(60, 10, 8, 12, 60, True, tail=(10, 48))
assert any(o["admitted"] and o["reply_s"] > 60 for o in out.values())
print("test_stream: OK")

"""Chapter 1 exercise: Kill the worker.

Kill the worker process with SIGKILL after the refund payment lands and before the
ledger records it, while a second worker polls. Predict first: does Asha get two
replies, or two refunds?

The lease keeps worker2 out while worker1 holds the job. When the lease runs out,
worker2 takes the job and the Vol 2 ledger, keyed by the job id, finds the payment
already made: no second call. One payment, one reply.
"""
import _path  # noqa: F401

import lab
import service

lines = []
r = lab.kill_and_resume(echo=lines.append)
for line in lines:
    print(line)

assert r["status"] == (202, 202, 401)
assert r["created"] == (True, False)            # the client retry is the same job
assert r["customer_id"] == "asha"               # the body said c-42; the session won
assert r["payments"] == 1, r                    # one payment at the provider
assert r["replies"] == 1, r                     # one reply to Asha
assert r["state"] == "DONE" and r["owner"] == "worker2"
assert r["payment_calls_on_resume"] == 0        # worker2 reconciled, did not pay again

# the fence: worker1 cannot finish a job it no longer holds, even if it wakes up
q = service.Queue(r["path"])
assert not q.complete("worker1", r["job_id"], 1, {"late": True})

# pause-expire-resume: the old claim cannot finish, even under a reused name
p = lab.pause_expire_resume(echo=print)
assert (p["old"], p["new"], p["late_done"], p["new_done"], p["state"]) == \
    (1, 2, False, True, "DONE"), p
print("ch01 solution: OK")

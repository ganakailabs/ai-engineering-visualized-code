"""Implementation test for Chapter 1: SIGKILL mid-job, real processes, one payment."""
import _path  # noqa: F401

import lab

r = lab.kill_and_resume(echo=lambda line: None)
assert (r["payments"], r["replies"], r["state"], r["owner"]) == (1, 1, "DONE", "worker2"), r
assert r["payment_calls_on_resume"] == 0
print("test_kill: OK")

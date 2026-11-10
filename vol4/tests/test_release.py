"""Implementation test for Chapter 6: CI blocks a critical case, the in-flight job
pays once on its own release, rollback keeps the deletion."""
import _path  # noqa: F401

import ch06
import release as R

assert R.ci("prompt v7", "prompt v8")["critical"] == ["SC-002"]
assert R.ci("prompt v7", "prompt v8")["verdict"] == "blocked"
assert "missing eval_report" in R.check(R.load("rel-15"))

ck = R.checkpoint("rel-14", "v2", {"refund-2001"})
for reader in (lambda: R.resume(ck, "v2", pay), lambda: R.resume(R.migrate_v2_v3(ck), "v3", pay)):
    pay = ["refund-2001"]
    reader()
    assert pay == ["refund-2001"], pay                  # one payment either way
pay = ["refund-2001"]
R.resume({"ledger": ["refund-2001"]}, "v3", pay)
assert len(pay) == 2                                    # the Break: unversioned checkpoint

dep = ch06.deletion_after_release()
assert dep.rollback("rel-14") == 2 and "mem-asha-1" not in dep.data and dep.live == "rel-14"
naive = ch06.deletion_after_release()
naive.rollback_naive("rel-14")
assert "mem-asha-1" in naive.data                       # what the naive restore does
# the release matrix: pinning keeps state readable; it does not authorize the next action
job = {"release": "rel-14", "effects": True, "next_op": "issue_refund"}
assert R.route_job(job, "rel-15").startswith("finish on rel-14")
assert R.route_job(job, "rel-15", {"issue_refund"}).startswith("pause")
assert R.route_job(dict(job, effects=False), "rel-15", {"issue_refund"}) == "restart on rel-15"
print("test_release: OK")

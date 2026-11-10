"""Joined drill: one failure and recovery through the real modules.

The capstone simulator (capstone.py) counts decisions; this drill runs the job queue
(service.Queue), the action ledger (Vol 2 ledger.Ledger), the tracer (trace.Tracer)
and a file restore together, against a MOCK payment provider. Nothing in the queue,
the ledger or the trace is simulated: every printed state is read back from their
records. The provider is a fixture: a separate SQLite file that stands in for a
payment company's own record, which your backup never contains.

The failure: a worker pays a refund and dies before recording it, and then the job
database is lost and restored from a backup taken before the payment.
"""
import os
import shutil
import sqlite3
import tempfile

import _root  # noqa: F401

from ledger import Ledger, key_for
from service import Queue, SESSIONS, job_id_for, refund_rule
from store import ORDERS
from trace import Tracer


class Crash(Exception):
    """The worker process dies here: no except or finally of its own runs."""


class MockProvider:
    """A payment provider's record. idempotent=True honours the key (a second call
    with the same key returns the first payment); False pays again."""

    def __init__(self, path, idempotent=True):
        self.db = sqlite3.connect(path, isolation_level=None)
        self.idempotent = idempotent
        self.db.execute("CREATE TABLE IF NOT EXISTS pays (n INTEGER PRIMARY KEY, "
                        "key TEXT, order_id TEXT, amount INTEGER)")

    def pay(self, key, order_id, amount):
        if self.idempotent and self.find(key):
            return self.find(key)
        self.db.execute("INSERT INTO pays (key, order_id, amount) VALUES (?, ?, ?)",
                        (key, order_id, amount))
        return self.find(key)

    def find(self, key):
        r = self.db.execute("SELECT n, key FROM pays WHERE key = ? ORDER BY n",
                            (key,)).fetchone()
        return r and {"payment": r[0], "payment_key": r[1]}

    def count(self, key):
        return self.db.execute("SELECT COUNT(*) FROM pays WHERE key = ?",
                               (key,)).fetchone()[0]


def refund_op(job):
    order_id = job["body"]["order_id"]
    args = {"order_id": order_id, "amount": ORDERS[order_id]["amount"]}
    return f"{job['job_id']}/refund-{order_id}", args


def work(queue, ledger, provider, worker, job_id, claim, now, crash=False):
    """One leased job: decide with code, pay through the ledger, reply, complete."""
    job = queue.get(job_id)
    ok, clause = refund_rule(ORDERS[job["body"]["order_id"]])
    op_id, args = refund_op(job)
    calls = []

    def call(key):
        calls.append(key)
        paid = provider.pay(key, args["order_id"], args["amount"])
        if crash:
            raise Crash("paid, not recorded")
        return paid

    row = ledger.execute(op_id, args, call, provider.find)
    queue.db.execute("INSERT OR IGNORE INTO replies VALUES (?, ?)",
                     (job_id, f"Refund of INR {args['amount']} is on its way ({clause})."))
    done = queue.complete(worker, job_id, claim, {"clause": clause}, now=now)
    return {"ledger": row["state"], "calls": len(calls), "done": done}


def reconcile_restored(ledger, queue, provider, job_ids):
    """Before any worker resumes after a restore: for each job, look up the payment
    key at the provider. A payment the ledger does not know about is recorded as
    CONFIRMED with the provider's receipt; nothing is called."""
    out = {}
    for job_id in job_ids:
        op_id, args = refund_op(queue.get(job_id))
        key = key_for(op_id, args)
        found = provider.find(key)
        row = ledger.row(op_id)
        if found and (row is None or row["state"] != "CONFIRMED"):
            ledger.prepare(op_id, args)
            ledger._move(op_id, "PREPARED", "SUBMITTED")
            ledger._move(op_id, "SUBMITTED", "CONFIRMED", found)
            out[job_id] = "recorded from provider"
        else:
            out[job_id] = "nothing to record"
    return out


def run(reconcile=True, idempotent=True, echo=print):
    """The drill in a temp directory. Returns the trusted counts the tests assert on."""
    tmp = tempfile.mkdtemp(prefix="aiev-v4-drill-")
    try:
        return _run(tmp, reconcile, idempotent, echo)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _run(tmp, reconcile, idempotent, echo):
    jobs, backup = os.path.join(tmp, "jobs.db"), os.path.join(tmp, "backup.db")
    provider = MockProvider(os.path.join(tmp, "provider.db"), idempotent)
    tr = Tracer(seed=16)
    ident = SESSIONS["s-asha"]
    job_id = job_id_for(ident, "T-2001")
    t0 = 1_000_000.0                                     # explicit lease clock

    q = Queue(jobs)
    led = Ledger(jobs, lease_s=3.0)
    root = tr.start("drill " + job_id, attrs={"job.id": job_id})
    q.enqueue(job_id, ident, "T-2001", {"order_id": "2001"})
    q.db.execute("PRAGMA wal_checkpoint(FULL)")
    shutil.copy(jobs, backup)
    tr.start("backup", parent=root, attrs={"job.state": q.get(job_id)["state"]})
    echo(f"enqueue {job_id}: {q.get(job_id)['state']}; backup taken")

    claim = q.lease("w1", job_id, now=t0)
    pay = tr.start("w1 refund", parent=root, attrs={"claim": claim})
    try:
        work(q, led, provider, "w1", job_id, claim, t0 + 1, crash=True)
    except Crash:
        pass
    op_id, args = refund_op(q.get(job_id))
    key = key_for(op_id, args)
    state = led.row(op_id)["state"]
    pay["attrs"].update({"ledger.state": state, "provider.rows": provider.count(key)})
    echo(f"w1 claim={claim} paid key={key}, crashed before recording")
    echo(f"  ledger {state}, provider rows={provider.count(key)}, "
         f"job {q.get(job_id)['state']}")

    q.db.close()
    led.db.close()
    for suffix in ("-wal", "-shm"):
        if os.path.exists(jobs + suffix):
            os.remove(jobs + suffix)
    shutil.copy(backup, jobs)                            # workers are stopped first
    q, led = Queue(jobs), Ledger(jobs, lease_s=3.0)
    ledger_rows = led.db.execute("SELECT COUNT(*) FROM ops").fetchone()[0]
    tr.start("restore", parent=root, attrs={"job.state": q.get(job_id)["state"],
                                            "ledger.rows": ledger_rows})
    echo(f"workers stopped; restore from backup: job {q.get(job_id)['state']}")
    echo(f"  ledger rows={ledger_rows}, provider rows={provider.count(key)} "
         "(the provider is not restored)")

    if reconcile:
        result = reconcile_restored(led, q, provider, [job_id])[job_id]
        tr.start("reconcile", parent=root, attrs={"result": result})
        echo(f"reconcile before resume: {result} -> ledger {led.row(op_id)['state']}")
    else:
        echo("no reconcile: resume straight after the restore")

    claim2 = q.lease("w2", job_id, now=t0 + 10)
    r = work(q, led, provider, "w2", job_id, claim2, t0 + 11)
    tr.start("w2 resume", parent=root, attrs={"claim": claim2, "calls": r["calls"],
                                              "ledger.state": r["ledger"]})
    echo(f"w2 claim={claim2}: payment calls={r['calls']}, ledger {r['ledger']}, "
         f"job {q.get(job_id)['state']}")
    stale = q.complete("w1", job_id, claim, {"clause": "late"}, now=t0 + 12)
    replies = q.db.execute("SELECT COUNT(*) FROM replies").fetchone()[0]
    paid = provider.count(key)
    echo(f"late w1 complete claim={claim}: {'accepted' if stale else 'refused'}"
         + (" (the restore rewound claim numbers)" if claim2 == claim else ""))
    echo(f"provider payments for key={paid}, replies={replies}, "
         f"double payments={max(0, paid - 1)}")
    echo(f"trace {root['trace_id'][:8]}:")
    for s in tr.spans[1:]:
        attrs = " ".join(f"{k}={v}" for k, v in s["attrs"].items())
        echo(f"  {s['name']:<11} {attrs}")
    q.db.close()
    led.db.close()
    provider.db.close()
    return {"payments": paid, "replies": replies, "stale_accepted": stale,
            "claim_after_restore": claim2}


def main():
    print("Joined drill: real queue, ledger, trace and restore; mock payment provider")
    print("\nA. reconcile before resume (the runbook)")
    run(reconcile=True, idempotent=True)
    print("\nB. no reconcile, provider honours the key")
    run(reconcile=False, idempotent=True)
    print("\nC. no reconcile, provider ignores the key")
    run(reconcile=False, idempotent=False)


if __name__ == "__main__":
    main()

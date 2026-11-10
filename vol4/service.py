"""Chapter 1: the service lab. An HTTP API, a SQLite job queue with leases, workers.

MM-147 Request Path, Job Path: the request path answers while the customer waits
       (accept the ticket, return 202 and a job id); the job path runs the long or
       risky work from a queue, and any worker can resume it from stored state.

This is a LAB, not a deployment. Python's own documentation says http.server "is not
recommended for production" (docs.python.org, checked Nov 4, 2026). The lab proves
four things: identity comes from the session, a lease lets only one worker own a job,
a claim number fences a paused worker out, and a killed worker's job is resumed once. docs/adr-001.md lists what it does not prove.
"""
import json
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import _root  # noqa: F401  (Vol 2 ledger, Vol 1 store)

from ledger import Ledger, key_for
from store import ORDERS, TODAY
from world import OWNERS

# Fixture login sessions (fictional). Identity comes from here, never from the body.
SESSIONS = {"s-asha": {"tenant_id": "a", "customer_id": "asha"}}
LEASE_S = 3.0          # lab value, chosen so the kill test runs in seconds; not a recommendation


def connect(path):
    db = sqlite3.connect(path, isolation_level=None, timeout=10)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE IF NOT EXISTS jobs (job_id TEXT PRIMARY KEY, tenant_id TEXT, "
               "customer_id TEXT, ticket_id TEXT, body TEXT, state TEXT, owner TEXT, "
               "lease_until REAL, attempts INTEGER DEFAULT 0, result TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS payments (key TEXT PRIMARY KEY, order_id TEXT, "
               "amount INTEGER)")                       # the mock payment provider's record
    db.execute("CREATE TABLE IF NOT EXISTS replies (job_id TEXT PRIMARY KEY, text TEXT)")
    return db


class Queue:
    """Jobs move QUEUED -> LEASED -> DONE. A lease is a time-limited claim: while it
    holds, no other worker may take the job; when it runs out, the job is free again."""

    def __init__(self, path):
        self.path, self.db = path, connect(path)

    def enqueue(self, job_id, identity, ticket_id, body):
        """Idempotent: the same job id twice is one job (a client retry, not a new ticket)."""
        cur = self.db.execute(
            "INSERT OR IGNORE INTO jobs (job_id, tenant_id, customer_id, ticket_id, body, "
            "state) VALUES (?, ?, ?, ?, ?, 'QUEUED')",
            (job_id, identity["tenant_id"], identity["customer_id"], ticket_id, json.dumps(body)))
        return cur.rowcount == 1

    def lease(self, worker, job_id, lease_s=LEASE_S, now=None):
        """Compare-and-set in one statement: take the job only if nobody holds a live
        lease. Returns the claim number (1, 2, ...) or 0. Each claim gets a new number,
        so a paused worker that wakes up holds an old claim even if its name is reused."""
        now = time.time() if now is None else now
        self.db.execute("BEGIN IMMEDIATE")
        try:
            cur = self.db.execute(
                "UPDATE jobs SET state = 'LEASED', owner = ?, lease_until = ?, "
                "attempts = attempts + 1 WHERE job_id = ? AND (state = 'QUEUED' OR "
                "(state = 'LEASED' AND lease_until <= ?))",
                (worker, now + lease_s, job_id, now))
            claim = 0
            if cur.rowcount == 1:
                claim = self.db.execute("SELECT attempts FROM jobs WHERE job_id = ?",
                                        (job_id,)).fetchone()[0]
        finally:
            self.db.execute("COMMIT")
        return claim

    def complete(self, worker, job_id, claim, result, now=None):
        """Only the current claim may finish the job: a fence against a slow worker
        that lost its lease and wakes up later. The claim number, not the worker's
        name, is the fence, so a restarted worker with the same name cannot pass
        for the old one. The fence guards this job row only; a payment's safety
        comes from the ledger key and the provider's idempotency contract."""
        now = time.time() if now is None else now
        cur = self.db.execute(
            "UPDATE jobs SET state = 'DONE', result = ? WHERE job_id = ? AND owner = ? "
            "AND attempts = ? AND state = 'LEASED' AND lease_until > ?",
            (json.dumps(result), job_id, worker, claim, now))
        return cur.rowcount == 1

    def get(self, job_id):
        r = self.db.execute("SELECT job_id, tenant_id, customer_id, ticket_id, body, state, "
                            "owner, lease_until, attempts, result FROM jobs WHERE job_id = ?",
                            (job_id,)).fetchone()
        keys = ("job_id", "tenant_id", "customer_id", "ticket_id", "body", "state", "owner",
                "lease_until", "attempts", "result")
        return r and dict(zip(keys, r), body=json.loads(r[4]))


def job_id_for(identity, ticket_id):
    """The job id is the business operation id:
    stable across client retries."""
    return f"op-{identity['tenant_id']}-{ticket_id}"


# ---- the request path: accept, check identity, enqueue, answer 202 ----------------

def make_handler(queue_path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):                  # keep the lab quiet
            pass

        def _send(self, code, obj):
            data = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            if self.path != "/tickets":
                return self._send(404, {"error": "not found"})
            token = self.headers.get("Authorization", "").removeprefix("Bearer ")
            identity = SESSIONS.get(token)
            if identity is None:
                return self._send(401, {"error": "no session"})
            n = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(n) or b"{}")
            # body["customer_id"], if a caller sends one, is ignored: the session decides
            job_id = job_id_for(identity, body["ticket_id"])
            created = Queue(queue_path).enqueue(job_id, identity, body["ticket_id"],
                                                {"order_id": body["order_id"],
                                                 "text": body["text"]})
            return self._send(202, {"job_id": job_id, "created": created, **identity})
    return Handler


def start_api(queue_path):
    connect(queue_path).close()
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(queue_path))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


# ---- the job path: decide from records, refund through the Vol 2 ledger -----------

def refund_rule(order):
    """R1-R3 on one order record (code decides, as in Vol 3 Ch 1)."""
    days = (TODAY - order["delivered"]).days
    if order["final_sale"]:
        return False, "R3"
    if order["damaged"]:
        return days <= 7, "R2"
    return days <= 30, "R1"


def run_job(queue, worker, job_id, claim, on_payment=None):
    """One worker runs one leased job. The refund is a Vol 2 ledger operation whose id
    comes from the job id, so a second worker that resumes the job reuses the same
    key and reconciles instead of paying twice."""
    job = queue.get(job_id)
    order_id = job["body"]["order_id"]
    order = ORDERS[order_id]
    ok, clause = refund_rule(order)
    called, before = [], None
    if OWNERS.get(order_id) != job["customer_id"]:
        ok, clause = False, "not your order"     # the job's identity came from the session
    if not ok:
        reply = f"Order #{order_id} cannot be refunded ({clause})."
    else:
        db = connect(queue.path)
        ledger = Ledger(queue.path, lease_s=LEASE_S)
        args = {"order_id": order_id, "amount": order["amount"]}

        op_id = f"{job_id}/refund-{order_id}"
        before = (ledger.row(op_id) or {}).get("state")

        def call(key):
            called.append(key)
            db.execute("INSERT OR IGNORE INTO payments VALUES (?, ?, ?)",
                       (key, order_id, order["amount"]))
            if on_payment:
                on_payment()                      # the lab's kill point: paid, not recorded
            return {"payment_key": key}

        def find(key):
            r = db.execute("SELECT key FROM payments WHERE key = ?", (key,)).fetchone()
            return r and {"payment_key": r[0]}

        row = ledger.execute(op_id, args, call, find)
        if row["state"] != "CONFIRMED":
            return {"state": row["state"], "ledger_before": before}  # next lease or a person
        reply = f"Refund of INR {order['amount']} for order #{order_id} is on its way ({clause})."
    queue.db.execute("INSERT OR IGNORE INTO replies VALUES (?, ?)", (job_id, reply))
    done = queue.complete(worker, job_id, claim, {"clause": clause})
    return {"state": "DONE" if done else "LEASE_LOST", "clause": clause,
            "ledger_before": before, "ledger_after": row["state"] if ok else None,
            "payment_calls": len(called)}


def counts(path, job_id):
    """Trusted state the tests assert on: payments and replies, not printed lines."""
    db = connect(path)
    pays = db.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
    reps = db.execute("SELECT COUNT(*) FROM replies WHERE job_id = ?", (job_id,)).fetchone()[0]
    return pays, reps


__all__ = ["Queue", "SESSIONS", "LEASE_S", "start_api", "run_job", "counts", "job_id_for",
           "key_for", "refund_rule"]

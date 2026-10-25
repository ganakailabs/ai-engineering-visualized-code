"""Chapter 6: side effects. The action ledger.

MM-155 One Operation, One Receipt: every write is a ledger row that moves
       PREPARED -> SUBMITTED -> CONFIRMED, or to UNKNOWN when the reply is lost.
       The key is written before the call and bound to the operation and its exact
       arguments; UNKNOWN is reconciled against the receiver's record, never retried blind.
       A process can die while a row is SUBMITTED; no except or finally block runs then.
       Each claim carries a lease, and a fresh worker treats a SUBMITTED row whose lease
       ran out as UNKNOWN: it reconciles first and decides about a retry only after.
MM-156 Compensation Is a New Action: undoing a confirmed write is another keyed
       operation that can fail; some writes (a paid refund) cannot be undone at all.
"""
import hashlib
import json
import sqlite3
import time

from world import WorldError

MOVES = {"PREPARED": {"SUBMITTED"},
         "SUBMITTED": {"CONFIRMED", "UNKNOWN", "FAILED"},   # UNKNOWN also on lease expiry
         "UNKNOWN": {"CONFIRMED", "PREPARED", "NEEDS_HUMAN"},
         "CONFIRMED": {"COMPENSATING", "NEEDS_HUMAN"},
         "COMPENSATING": {"COMPENSATED", "NEEDS_HUMAN"}}


class LookupUnavailable(Exception):
    """find() could not answer (outage, timeout): the result stays UNKNOWN."""


class ArgsChanged(Exception):
    """The same operation was asked for with different arguments."""


def canonical(args):
    return json.dumps(args, sort_keys=True, separators=(",", ":"))


def key_for(op_id, args):
    """One key per operation AND its exact arguments."""
    return "k-" + hashlib.sha256(f"{op_id}|{canonical(args)}".encode()).hexdigest()[:10]


class Ledger:
    def __init__(self, path=":memory:", lease_s=300, absent_means_not_applied=True):
        """lease_s: how long a SUBMITTED claim is trusted to a live worker.
        absent_means_not_applied: the receiver contract. True only when find() reads an
        authoritative record that shows every applied write (the mock payments record).
        Without that contract a missing lookup leaves the operation UNKNOWN."""
        self.db = sqlite3.connect(path, isolation_level=None)
        self.lease_s, self.absent_definite = lease_s, absent_means_not_applied
        self.db.execute("CREATE TABLE IF NOT EXISTS ops (op_id TEXT PRIMARY KEY, "
                        "key TEXT, args TEXT, state TEXT, receipt TEXT)")
        cols = {r[1] for r in self.db.execute("PRAGMA table_info(ops)")}
        if "claimed_at" not in cols:
            self.db.execute("ALTER TABLE ops ADD COLUMN claimed_at REAL")

    def row(self, op_id):
        r = self.db.execute("SELECT key, args, state, receipt FROM ops WHERE op_id = ?",
                            (op_id,)).fetchone()
        return r and {"key": r[0], "args": json.loads(r[1]), "state": r[2],
                      "receipt": json.loads(r[3]) if r[3] else None}

    def _move(self, op_id, frm, to, receipt=None):
        """Compare-and-set: only a worker that sees state frm may move it to `to`."""
        assert to in MOVES.get(frm, set()), f"{frm} -> {to}"
        cur = self.db.execute("UPDATE ops SET state = ?, receipt = COALESCE(?, receipt), "
                              "claimed_at = ? WHERE op_id = ? AND state = ?",
                              (to, receipt and json.dumps(receipt),
                               time.time() if to == "SUBMITTED" else None, op_id, frm))
        return cur.rowcount == 1

    def prepare(self, op_id, args):
        """Write the key BEFORE the call. A retry or replan gets the same row back."""
        key = key_for(op_id, args)
        self.db.execute("INSERT OR IGNORE INTO ops (op_id, key, args, state) VALUES (?, ?, ?, 'PREPARED')",
                        (op_id, key, canonical(args)))
        row = self.row(op_id)
        if row["args"] != json.loads(canonical(args)):
            raise ArgsChanged(f"{op_id} was prepared with {row['args']}, not {args}")
        return row

    def execute(self, op_id, args, call, find):
        """call(key) writes; find(key) reads the receiver's record."""
        row = self.prepare(op_id, args)
        if row["state"] == "SUBMITTED" and op_id in self.abandoned():
            # the claimant died mid-call: the effect may or may not have landed
            self._move(op_id, "SUBMITTED", "UNKNOWN")
            row = self.row(op_id)
        if row["state"] == "UNKNOWN":
            row = self.reconcile(op_id, find)
        # done, or another worker has it
        if row["state"] != "PREPARED":
            return row
        if not self._move(op_id, "PREPARED", "SUBMITTED"):
            # lost the claim to another worker
            return self.row(op_id)
        try:
            receipt = call(row["key"])
        except WorldError as e:
            self._move(op_id, "SUBMITTED",
                       "UNKNOWN" if e.transient else "FAILED")
            return dict(self.row(op_id), error=e.code)
        self._move(op_id, "SUBMITTED", "CONFIRMED", receipt)
        return self.row(op_id)

    def abandoned(self):
        """SUBMITTED rows whose claim lease has run out: their worker is presumed dead."""
        cutoff = time.time() - self.lease_s
        return [r[0] for r in self.db.execute(
            "SELECT op_id FROM ops WHERE state = 'SUBMITTED' AND "
            "(claimed_at IS NULL OR claimed_at <= ?) ORDER BY op_id", (cutoff,))]

    def recover(self, find):
        """Recovery scan for a fresh worker: reconcile every abandoned claim."""
        out = {}
        for op_id in self.abandoned():
            self._move(op_id, "SUBMITTED", "UNKNOWN")
            out[op_id] = self.reconcile(op_id, find)["state"]
        return out

    def reconcile(self, op_id, find):
        """UNKNOWN is a state: check the receiver by key first.
        FOUND -> CONFIRMED. Not found under the receiver contract -> definitely not
        applied, PREPARED (the same key is reused). A lookup that cannot answer, or
        not-found without the contract -> still UNKNOWN; never a blind retry."""
        row = self.row(op_id)
        try:
            found = find(row["key"])
        except LookupUnavailable:
            return dict(self.row(op_id), lookup="unavailable")
        if found:
            self._move(op_id, row["state"], "CONFIRMED", found)
        elif row["state"] == "UNKNOWN" and self.absent_definite:
            # the authoritative record says it never landed: safe, same key
            self._move(op_id, "UNKNOWN", "PREPARED")
        return self.row(op_id)

    def compensate(self, op_id, undo, comp_args):
        """MM-156: a new keyed operation. undo is None when the write cannot be undone."""
        if undo is None:
            self._move(op_id, "CONFIRMED", "NEEDS_HUMAN")
            return self.row(op_id)
        self._move(op_id, "CONFIRMED", "COMPENSATING")
        comp = self.execute(f"undo-{op_id}", comp_args, undo, lambda key: None)
        self._move(op_id, "COMPENSATING",
                   "COMPENSATED" if comp["state"] == "CONFIRMED" else "NEEDS_HUMAN")
        return dict(self.row(op_id), compensation=comp)

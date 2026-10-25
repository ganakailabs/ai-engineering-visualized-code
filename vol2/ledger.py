"""Chapter 6: side effects. The action ledger.

MM-155 One Operation, One Receipt: every write is a ledger row that moves
       PREPARED -> SUBMITTED -> CONFIRMED, or to UNKNOWN when the reply is lost.
       The key is written before the call and bound to the operation and its exact
       arguments; UNKNOWN is reconciled against the receiver's record, never retried blind.
MM-156 Compensation Is a New Action: undoing a confirmed write is another keyed
       operation that can fail; some writes (a paid refund) cannot be undone at all.
"""
import hashlib
import json
import sqlite3

from world import WorldError

MOVES = {"PREPARED": {"SUBMITTED"},
         "SUBMITTED": {"CONFIRMED", "UNKNOWN", "FAILED"},
         "UNKNOWN": {"CONFIRMED", "PREPARED", "NEEDS_HUMAN"},
         "CONFIRMED": {"COMPENSATING", "NEEDS_HUMAN"},
         "COMPENSATING": {"COMPENSATED", "NEEDS_HUMAN"}}


class ArgsChanged(Exception):
    """The same operation was asked for with different arguments."""


def canonical(args):
    return json.dumps(args, sort_keys=True, separators=(",", ":"))


def key_for(op_id, args):
    """One key per operation AND its exact arguments."""
    return "k-" + hashlib.sha256(f"{op_id}|{canonical(args)}".encode()).hexdigest()[:10]


class Ledger:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.execute("CREATE TABLE IF NOT EXISTS ops (op_id TEXT PRIMARY KEY, "
                        "key TEXT, args TEXT, state TEXT, receipt TEXT)")

    def row(self, op_id):
        r = self.db.execute("SELECT key, args, state, receipt FROM ops WHERE op_id = ?",
                            (op_id,)).fetchone()
        return r and {"key": r[0], "args": json.loads(r[1]), "state": r[2],
                      "receipt": json.loads(r[3]) if r[3] else None}

    def _move(self, op_id, frm, to, receipt=None):
        """Compare-and-set: only a worker that sees state frm may move it to `to`."""
        assert to in MOVES.get(frm, set()), f"{frm} -> {to}"
        cur = self.db.execute("UPDATE ops SET state = ?, receipt = COALESCE(?, receipt) "
                              "WHERE op_id = ? AND state = ?",
                              (to, receipt and json.dumps(receipt), op_id, frm))
        return cur.rowcount == 1

    def prepare(self, op_id, args):
        """Write the key BEFORE the call. A retry or replan gets the same row back."""
        key = key_for(op_id, args)
        self.db.execute("INSERT OR IGNORE INTO ops VALUES (?, ?, ?, 'PREPARED', NULL)",
                        (op_id, key, canonical(args)))
        row = self.row(op_id)
        if row["args"] != json.loads(canonical(args)):
            raise ArgsChanged(f"{op_id} was prepared with {row['args']}, not {args}")
        return row

    def execute(self, op_id, args, call, find):
        """call(key) writes; find(key) reads the receiver's record."""
        row = self.prepare(op_id, args)
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

    def reconcile(self, op_id, find):
        """UNKNOWN is a state: check the receiver by key first."""
        row = self.row(op_id)
        found = find(row["key"])
        if found:
            self._move(op_id, row["state"], "CONFIRMED", found)
        elif row["state"] == "UNKNOWN":
            # it never landed: safe, same key
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

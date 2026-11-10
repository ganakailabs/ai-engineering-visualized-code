"""Privacy and data lifecycle for Chapter 14: the data map, an anchored audit trail,
export and delete across every store, and a restore that keeps deleted data deleted.

All stores are in-memory stand-ins with fictional data (SIMULATED). The checkpoint safe
stands in for storage the log writer cannot rewrite (a separate account, a write-once
bucket, or signed digest files); here it is just a separate object. Not legal advice:
retention periods are placeholders for your own legal and finance teams to set.
"""
import copy
import hashlib
import json

# The lab FIXTURE's stores, not every store a deployment has.
# store -> (what it holds, how it is erased, retention placeholder)
# Linkable ids (customer, session, order) can still be personal data: rows that keep
# ids by policy say so, and have their own access and retention rules.
DATA_MAP = {
    "jobs":     ("ticket text, ids",          "ours",   "P days"),
    "replies":  ("reply text",                "ours",   "P days"),
    "memory":   ("notes from past chats",     "ours",   "until deleted"),
    "index":    ("chunks of past tickets",    "ours",   "rebuilt nightly"),
    "logs":     ("redacted records, ids",     "ours",   "L days"),
    "evals":    ("cases from feedback (Ch 5)", "ours",  "E days"),
    "train":    ("training export (Ch 12)",   "ours",   "T days"),
    "cache":    ("general answers (Ch 9)",    "flush",  "until version"),
    "audit":    ("actor, action, ids",        "policy", "A days"),
    "journal":  ("customer id per deletion",  "policy", "oldest backup"),
    "provider": ("prompts sent to model API", "per",    "provider terms"),
    "backups":  ("nightly copy of live",      "expiry", "B days"),
}
LIVE = ["jobs", "replies", "memory", "index", "logs", "evals", "train", "cache"]
# How a provider row is erased, recorded per product with the date it was read. The
# lab names no real provider; these are the KINDS of mechanism to look for.
PROVIDER_ERASURE = ["deletion API or console per stored object",
                    "retention setting (e.g. zero or short retention)",
                    "contractual term with a stated period"]


def fixture():
    """Fictional stores. Asha (customer asha) and Ravi (customer ravi)."""
    return {
        "jobs": [{"customer": "asha", "text": "mug set #2001 arrived cracked"},
                 {"customer": "asha", "text": "where is order #2002?"},
                 {"customer": "ravi", "text": "kettle #3001 is late"}],
        "replies": [{"customer": "asha", "text": "Sorry, a refund is on its way."},
                    {"customer": "ravi", "text": "It ships tomorrow."}],
        "memory": [{"customer": "asha", "text": "prefers email updates"},
                   {"customer": "asha", "text": "had a cracked mug set before"}],
        "index": [{"customer": "asha", "text": "chunk: mug set arrived cracked"},
                  {"customer": "asha", "text": "chunk: where is order 2002"},
                  {"customer": "asha", "text": "chunk: refund confirmed"},
                  {"customer": "ravi", "text": "chunk: kettle late"}],
        "logs": [{"customer": "asha", "text": "job done route=refund"},
                 {"customer": "ravi", "text": "job done route=status"}],
        "evals": [{"customer": "asha", "text": "case SC-031 masked: mug [ITEM] cracked"}],
        "train": [{"customer": "asha", "text": "my mug set arrived cracked -> refund"},
                  {"customer": "ravi", "text": "kettle is late -> delivery"}],
        "cache": [{"customer": None, "text": "Orders usually arrive in 5 days (S1)."}],
    }


def export(stores, customer):
    """Count every record per store on the map. Provider and backups are listed
    with what we can say about them, not silently skipped."""
    return {s: sum(r["customer"] == customer for r in stores.get(s, []))
            for s in LIVE}


def delete(stores, customer, journal):
    removed = {}
    for s in LIVE:
        before = len(stores[s])
        stores[s] = [r for r in stores[s] if r["customer"] != customer]
        removed[s] = before - len(stores[s])
    journal.append({"op": "delete", "customer": customer})
    return removed


def backup(stores):
    return copy.deepcopy(stores)


def restore(snapshot, journal=None):
    stores = copy.deepcopy(snapshot)
    for entry in journal or []:          # replay every deletion since the snapshot
        if entry["op"] == "delete":
            delete(stores, entry["customer"], [])
    return stores


def present(stores, customer):
    return any(export(stores, customer).values())


# --- the audit trail -------------------------------------------------------------

def _digest(entry, prev):
    body = json.dumps(entry, sort_keys=True) + prev
    return hashlib.sha256(body.encode()).hexdigest()


class AuditLog:
    """Hash-chained entries. Every N entries a checkpoint (seq, hash) goes to the safe,
    which the writer cannot rewrite. The actor comes from the session, never from the
    caller's arguments."""

    def __init__(self, safe, every=5):
        self.rows, self.safe, self.every = [], safe, every

    def append(self, session, action, **fields):
        fields.pop("actor", None)        # a caller cannot name the actor
        entry = {"seq": len(self.rows) + 1,
                 "actor": f"{session['kind']}({session['id']})",
                 "action": action, **fields}
        prev = self.rows[-1]["hash"] if self.rows else "genesis"
        self.rows.append({"entry": entry, "hash": _digest(entry, prev)})
        if entry["seq"] % self.every == 0:
            self.safe.append((entry["seq"], self.rows[-1]["hash"]))
        return entry


def verify(rows, safe, latest_expected=None):
    """-> (ok, reason). Recompute the chain, then compare it with the checkpoints.
    latest_expected: the newest checkpoint seq, known from somewhere the writer cannot
    touch (a monitor, a counter, a signed digest's sequence). Without it, an attacker
    who can remove the newest checkpoints and cut the log back to an older valid one
    passes: every remaining checkpoint is genuine (a rollback)."""
    prev, hashes = "genesis", {}
    for r in rows:
        h = _digest(r["entry"], prev)
        if h != r["hash"]:
            return False, f"chain broken at entry {r['entry']['seq']}"
        hashes[r["entry"]["seq"]] = h
        prev = h
    for seq, h in safe:
        if seq not in hashes:
            return False, f"truncated: checkpoint {seq} missing"
        if hashes[seq] != h:
            return False, f"checkpoint {seq} mismatch"
    if latest_expected is not None and latest_expected not in {s for s, _ in safe}:
        return False, f"rollback: checkpoint {latest_expected} not in the safe"
    return True, "ok"


def rechain(rows):
    """What an attacker with write access to the log can do: recompute every hash."""
    prev, out = "genesis", []
    for r in rows:
        h = _digest(r["entry"], prev)
        out.append({"entry": r["entry"], "hash": h})
        prev = h
    return out

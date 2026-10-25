"""Chapter 9: agent memory. Lifetime, scope and correction.

MM-102 Memory by Lifetime and Scope: each record says how long it lives (turn,
       session, persistent), whose it is (ticket, customer, team), what it is (fact,
       preference, episode), where it came from and who may read it.
MM-103 Correct It Everywhere: a correction supersedes by key and reaches every copy:
       the store, the search index and the cached summary. Deletion does too.
Memory is never the source for business controls: the refund ledger is (Chapter 8).
"""
from datetime import timedelta

LIFETIMES = {"turn", "session", "persistent"}
SCOPES = {"ticket", "customer", "team"}
TYPES = {"fact", "preference", "episode"}


class Memory:
    def __init__(self, world):
        self.world = world
        self.store = {}            # id -> record (the source of truth)
        self.index = {}            # id -> indexed text (a copy, for search)
        self.summaries = {}        # scope_id -> cached text (a copy, for the prompt)
        self._n = 0

    def write(self, scope_id, key, value, lifetime, scope, type_, source,
              readers=("agent",), hours=None):
        assert lifetime in LIFETIMES and scope in SCOPES and type_ in TYPES
        self._n += 1
        rid = f"m-{self._n:03d}"
        expires = None
        if lifetime != "persistent":
            expires = (self.world.clock + timedelta(hours=hours or 1)).isoformat()
        self.store[rid] = {"id": rid, "scope_id": scope_id, "key": key, "value": value,
                           "lifetime": lifetime, "scope": scope, "type": type_,
                           "source": source, "readers": set(readers),
                           "at": self.world.now(), "expires": expires,
                           "superseded_by": None}
        self.index[rid] = f"{key} {value}".lower()
        self.summaries[scope_id] = self._summary(scope_id)
        return rid

    def _store_only(self, scope_id, key, value, template, source):
        """What a naive correction does: a new row in the store, nothing else."""
        self._n += 1
        rid = f"m-{self._n:03d}"
        self.store[rid] = dict(template, id=rid, value=value, source=source,
                               at=self.world.now(), superseded_by=None)
        return rid

    def live(self, scope_id, reader="agent"):
        return [r for r in self.store.values()
                if r["scope_id"] == scope_id and r["superseded_by"] is None
                and reader in r["readers"]]

    def _summary(self, scope_id):
        facts = [f"{r['key']}: {r['value']}" for r in self.live(scope_id)
                 if r["type"] != "episode"]
        return "; ".join(facts)

    def recall(self, scope_id, query="", reader="agent"):
        """Facts and episodes this reader may see, plus the cached summary."""
        words = query.lower().split()
        hits = {rid for rid, text in self.index.items() if any(w in text for w in words)}
        records = [r for r in self.live(scope_id, reader) if not words or r["id"] in hits]
        return {"summary": self.summaries.get(scope_id, ""),
                "episodes": [r for r in records if r["type"] == "episode"],
                "facts": [r for r in records if r["type"] != "episode"]}

    def correct(self, scope_id, key, value, source, propagate=True):
        """Supersede by key. propagate=False is the BREAK:
        only the store changes."""
        old = [r for r in self.live(scope_id) if r["key"] == key]
        template = old[0] if old else {"lifetime": "persistent", "scope": "customer",
                                       "type": "fact", "readers": {"agent"}}
        if not propagate:
            new = self._store_only(scope_id, key, value, old[0], source)
            for r in old:
                r["superseded_by"] = new
            return [r["id"] for r in old]
        t = template
        new = self.write(scope_id, key, value, t["lifetime"],
                         t["scope"], t["type"], source,
                         tuple(t["readers"]))
        for r in old:
            r["superseded_by"] = new
            self.index.pop(r["id"], None)   # the index copy
        # the summary copy
        self.summaries[scope_id] = self._summary(scope_id)
        return [r["id"] for r in old]

    def forget(self, scope_id):
        """Consent withdrawn: delete from the store, the index and the summaries."""
        gone = {rid for rid, r in self.store.items() if r["scope_id"] == scope_id}
        for rid in gone:
            del self.store[rid]
            self.index.pop(rid, None)
        self.summaries.pop(scope_id, None)
        return len(gone)

    def expire(self):
        """Turn and session memories end on schedule, in every copy."""
        now = self.world.now()
        gone = {rid for rid, r in self.store.items() if r["expires"] and r["expires"] <= now}
        for rid in gone:
            scope_id = self.store.pop(rid)["scope_id"]
            self.index.pop(rid, None)
            self.summaries[scope_id] = self._summary(scope_id)
        return len(gone)

    def copies_of(self, text):
        """Where does this text still live? (tests read this, not trace lines)"""
        return {"store": any(text in str(r["value"]) for r in self.store.values()
                             if r["superseded_by"] is None),
                "index": any(text.lower() in t for t in self.index.values()),
                "summary": any(text in s for s in self.summaries.values())}

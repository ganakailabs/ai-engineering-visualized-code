"""Index lifecycle: content, access and delete sync; build, check, switch (Vol 3 Ch 14).

The index is a copy of the sources. sync() detects three changes, each on its own:
content (text hash), access (a separate hash of the audience metadata) and deletes
(tombstoned). A new embedder means a migration: build a new index version beside the
old one, check it on the held-out retrieval set, and switch only if it passes. A
half-built index, or one that mixes embedders, is refused. Embedders are Ch 6's toys.

A version-only change (same text, same audience, new version number) is synced on
its own count, so answers cite the current version. A listing that is not known to
be complete (a source API that paged, timed out or filtered) never tombstones:
absence from a partial listing is not evidence of deletion.
The switch here returns a different Python object; a real store needs an atomic
alias or pointer swap, and a rollback path, to do the same thing safely.
"""
import hashlib

import _root  # noqa: F401

import vectors as V


def h(s):
    return hashlib.sha256(s.encode()).hexdigest()[:10]


def sources():
    """Fresh fixture: Ch 6's documents, all public, version 1."""
    return {i: dict(text=t, audience="customer", version=1) for i, t in V.DOCS.items()}


class IndexVersion:
    def __init__(self, name, model):
        self.name, self.model, self.rows, self.tombstones = name, model, {}, set()

    def put(self, i, doc):
        self.rows[i] = dict(vec=V.embed(doc["text"], self.model), model=self.model,
                            content=h(doc["text"]), access=h(doc["audience"]),
                            audience=doc["audience"], version=doc["version"])

    def search(self, q, audience="customer", k=1):
        qv = V.embed(q, self.model)
        hits = [(V.dot(qv, r["vec"]), i) for i, r in self.rows.items()
                if audience == "internal" or r["audience"] == "customer"]
        return [i for _, i in sorted(hits, reverse=True)[:k]]


def build(src, name, model):
    ix = IndexVersion(name, model)
    for i, d in src.items():
        ix.put(i, d)
    return ix


def sync(src, ix, complete=True):
    """Returns counts. Content, access and version are compared separately.
    complete=False means src may be a partial listing: nothing is tombstoned and the
    ids it did not list are counted as unlisted, for a later full sync."""
    changed = access_changed = version_changed = added = removed = unlisted = 0
    for i, d in src.items():
        r = ix.rows.get(i)
        if r is None:
            ix.put(i, d)
            added += 1
        elif r["content"] != h(d["text"]):
            ix.put(i, d)
            changed += 1
        elif r["access"] != h(d["audience"]):
            r.update(access=h(d["audience"]), audience=d["audience"], version=d["version"])
            access_changed += 1
        elif r["version"] != d["version"]:
            r.update(version=d["version"])
            version_changed += 1
    for i in [i for i in ix.rows if i not in src]:
        if not complete:
            unlisted += 1
            continue
        del ix.rows[i]
        ix.tombstones.add(i)
        removed += 1
    return dict(changed=changed, access_changed=access_changed, version_changed=version_changed,
                added=added, removed=removed, unlisted=unlisted)


def content_only_sync(src, ix):
    """The BREAK for permission-only updates: a content hash alone misses them."""
    return sum(1 for i, d in src.items() if i in ix.rows and ix.rows[i]["content"] != h(d["text"]))


def check(src, ix):
    orphans = [i for i in ix.rows if i not in src]
    stale = [i for i, d in src.items() if i in ix.rows and
             (ix.rows[i]["content"] != h(d["text"]) or ix.rows[i]["access"] != h(d["audience"])
              or ix.rows[i]["version"] != d["version"])]
    missing = [i for i in src if i not in ix.rows]
    mixed = len({r["model"] for r in ix.rows.values()}) > 1
    return dict(orphans=len(orphans), stale=len(stale), missing=len(missing), mixed=mixed)


def recall(ix):
    return sum(ix.search(q)[:1] == [want] for q, want in V.GOLDEN), len(V.GOLDEN)


def switch(live, candidate, src):
    """Build, check, switch: returns (new_live, reason)."""
    c = check(src, candidate)
    if c["missing"] or c["mixed"] or c["orphans"] or c["stale"]:
        return live, f"refused: not consistent {c}"
    new, old = recall(candidate), recall(live)
    if new[0] < old[0]:
        return live, f"refused: held-out recall {new[0]}/{new[1]} < live {old[0]}/{old[1]}"
    return candidate, f"switched: held-out recall {new[0]}/{new[1]} >= live {old[0]}/{old[1]}"

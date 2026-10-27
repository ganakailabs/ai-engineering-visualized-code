"""Embedders on your own set, a clustered (IVF-style) toy index, and the contract (Ch 6).

Two toy embedders stand in for real ones (both standard library, both fictional):
  "lexi-v1"  word hashing that folds digits away, like a general model that treats
             NW-500 and NW-550 as the same thing (the "leaderboard pick");
  "gram-v1"  character-trigram hashing that keeps product codes apart.
The index groups vectors around fixed centroids and searches only the nearest
`probe` groups. ANN recall is measured against exact search on the same vectors;
retrieval recall is measured against the golden set. The two never mix.
"""
import hashlib
import math
import re

import _root  # noqa: F401

DIM = 64
DOCS = {
    "nw500-batt": "NW-500 headphones battery replacement under warranty",
    "nw550-batt": "NW-550 headphones battery replacement paid service",
    "nw500-pair": "NW-500 headphones bluetooth pairing steps",
    "nw550-pair": "NW-550 headphones bluetooth pairing reset",
    "mug-dmg": "ceramic mug damaged in delivery refund with photo",
    "mug-care": "ceramic mug dishwasher and microwave care",
    "ret-30": "unused items refund within 30 days original packaging",
    "ret-final": "final sale items cannot be refunded",
    "ship-in": "standard delivery in India takes 3 to 5 days",
    "ship-eu": "delivery to the EU takes 7 to 10 days",
    "gift-card": "gift cards exchange for store credit",
    "acct-pw": "reset your account password from the login page",
}
GOLDEN = [   # (question, expected chunk id) - the retrieval golden set
    ("NW-550 battery replacement cost", "nw550-batt"),
    ("is the NW-500 battery covered", "nw500-batt"),
    ("pair my NW-550", "nw550-pair"),
    ("mug arrived broken", "mug-dmg"),
    ("how long does delivery to the EU take", "ship-eu"),
    ("can I return a final sale item", "ret-final"),
]


def _bucket(tok, salt):
    return int(hashlib.sha256(f"{salt}:{tok}".encode()).hexdigest(), 16) % DIM


def _norm(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def embed(text, model="gram-v1"):
    if model.startswith("ollama:"):            # optional real embedder, see runs/README.md
        from ollama_model import embed_ollama   # Vol 1, POST /api/embed, unit length
        return embed_ollama(text, model.split(":", 1)[1])
    v = [0.0] * DIM
    t = text.lower()
    if model.startswith("lexi"):
        toks = re.findall(r"[a-z]+", re.sub(r"\d", "", t))
    else:
        toks = [t[i:i + 3] for i in range(len(t) - 2)]
    for tok in toks:
        v[_bucket(tok, model)] += 1.0
    return _norm(v)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def recall_at(model, k=1):
    vecs = {d: embed(t, model) for d, t in DOCS.items()}
    hits = 0
    for q, want in GOLDEN:
        qv = embed(q, model)
        top = sorted(vecs, key=lambda d: (-dot(qv, vecs[d]), d))[:k]
        hits += want in top
    return hits, len(GOLDEN)


CONTRACT_KEYS = ("model", "version", "dim", "distance", "normalized", "encoding", "truncate")


def contract(model="gram-v1", version="v1"):
    return {"model": model, "version": version, "dim": DIM, "distance": "cosine",
            "normalized": True, "encoding": "same for query and document",
            "truncate": "none"}


class ClusteredIndex:
    """IVF-style: vectors sit in groups; a search opens only the `probe` nearest groups."""

    def __init__(self, docs=DOCS, model="gram-v1", seeds=("nw500-batt", "mug-dmg", "ret-30", "ship-eu")):
        self.contract = contract(model)
        self.vecs = {d: embed(t, model) for d, t in docs.items()}
        self.centroids = [self.vecs[s] for s in seeds]
        self.groups = {i: [] for i in range(len(seeds))}
        for d, v in self.vecs.items():
            self.groups[self._nearest(v, 1)[0]].append(d)

    def _nearest(self, v, n):
        order = sorted(range(len(self.centroids)), key=lambda i: -dot(v, self.centroids[i]))
        return order[:n]

    def check(self, query_contract):
        bad = [k for k in CONTRACT_KEYS if query_contract.get(k) != self.contract[k]]
        return bad

    def exact(self, qv, k=3):
        return sorted(self.vecs, key=lambda d: (-dot(qv, self.vecs[d]), d))[:k], len(self.vecs)

    def search(self, qv, k=3, probe=1):
        pool = [d for g in self._nearest(qv, probe) for d in self.groups[g]]
        return sorted(pool, key=lambda d: (-dot(qv, self.vecs[d]), d))[:k], len(pool)

    def query(self, text, query_contract, k=3, probe=1):
        bad = self.check(query_contract)
        if bad:
            raise ValueError(f"contract mismatch: {', '.join(bad)}")
        return self.search(embed(text, query_contract["model"]), k, probe)


def ann_recall(ix, questions, k=3, probe=1):
    found = total = compared = 0
    missed = []
    for q in questions:
        qv = embed(q, ix.contract["model"])
        ex, _ = ix.exact(qv, k)
        ann, n = ix.search(qv, k, probe)
        found += len(set(ex) & set(ann))
        total += len(ex)
        compared += n
        missed += [(q, d) for d in ex if d not in ann]
    return found, total, compared, missed

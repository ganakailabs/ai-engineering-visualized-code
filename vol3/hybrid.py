"""Hybrid search with an exact-match lane for identifiers (Vol 3 Ch 7).

Three lanes over the Ch 6 chunks (fictional): a word lane (BM25 on a plain analyzer),
a meaning lane (the Ch 6 toy embedder "gram-v1") and an EXACT
lane that matches normalized identifiers. Two fusions are compared: reciprocal rank
fusion (ranks only) and weighted score fusion (min-max normalized). The weight is chosen
on the DEV split and reported on the HELD-OUT split, per query type.
"""
import math
import re

import _root  # noqa: F401

import vectors as V

DOCS = V.DOCS
MEANING_MODEL = "gram-v1"   # the Ch 6 winner on the golden set
ID_RE = re.compile(r"\b([a-z]{2})[\s-]?(\d{3})\b", re.I)


def normalize_id(text):
    """'NW-500', 'nw500', 'nw 500' -> 'NW-500'. Returns every id found, in order."""
    return [f"{a.upper()}-{b}" for a, b in ID_RE.findall(text)]


def analyze(text):
    """The plain analyzer: lower case, split on anything that is not a letter or digit."""
    return re.findall(r"[a-z0-9]+", text.lower())


class BM25:
    def __init__(self, docs, k1=1.2, b=0.75):
        self.docs = {d: analyze(t) for d, t in docs.items()}
        self.avg = sum(map(len, self.docs.values())) / len(self.docs)
        self.k1, self.b = k1, b
        self.df = {}
        for toks in self.docs.values():
            for w in set(toks):
                self.df[w] = self.df.get(w, 0) + 1

    def scores(self, query):
        n, out = len(self.docs), {}
        for d, toks in self.docs.items():
            s = 0.0
            for w in analyze(query):
                f = toks.count(w)
                if f:
                    idf = math.log(1 + (n - self.df[w] + 0.5) / (self.df[w] + 0.5))
                    s += idf * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * len(toks) / self.avg))
            out[d] = s
        return out


WORDS = BM25(DOCS)
_VECS = {d: V.embed(t, MEANING_MODEL) for d, t in DOCS.items()}
DOC_IDS = {d: set(normalize_id(t)) for d, t in DOCS.items()}


def meaning_scores(query):
    q = V.embed(query, MEANING_MODEL)
    return {d: V.dot(q, v) for d, v in _VECS.items()}


def ranked(scores):
    return sorted(scores, key=lambda d: (-scores[d], d))


def rrf(lists, k=60):
    """Reciprocal rank fusion: ignores the score scales, uses only positions."""
    out = {}
    for lst in lists:
        for r, d in enumerate(lst, 1):
            out[d] = out.get(d, 0.0) + 1 / (k + r)
    return ranked(out)


def minmax(s):
    lo, hi = min(s.values()), max(s.values())
    return {d: (v - lo) / (hi - lo) if hi > lo else 0.0 for d, v in s.items()}


def score_fusion(query, w):
    """w * words + (1 - w) * meaning, each min-max normalized first."""
    a, b = minmax(WORDS.scores(query)), minmax(meaning_scores(query))
    return ranked({d: w * a[d] + (1 - w) * b[d] for d in DOCS})


def exact_lane(query):
    """A PRIORITY lane, not a hard filter: search() moves exact-id hits to the front
    and still returns every other result after them."""
    ids = normalize_id(query)
    return [d for d in sorted(DOCS) if ids and set(ids) <= DOC_IDS[d]], ids


def search(query, method="score", w=0.5, lane=True):
    if method == "words":
        out = ranked(WORDS.scores(query))
    elif method == "meaning":
        out = ranked(meaning_scores(query))
    elif method == "rrf":
        out = rrf([ranked(WORDS.scores(query)), ranked(meaning_scores(query))])
    else:
        out = score_fusion(query, w)
    if lane:
        hits, _ = exact_lane(query)        # exact hits go first, in fused order
        out = [d for d in out if d in hits] + [d for d in out if d not in hits]
    return out


# (query, expected chunk, type). Types: "id" names a product code, "meaning" does not.
DEV = [
    ("nw550 battery", "nw550-batt", "id"),
    ("connect nw500 to phone", "nw500-pair", "id"),
    ("NW550 reset", "nw550-pair", "id"),
    ("mug broken on arrival", "mug-dmg", "meaning"),
    ("refunds for unused things", "ret-30", "meaning"),
    ("shipping time India", "ship-in", "meaning"),
]
HELD_OUT = [
    ("battery for nw 550", "nw550-batt", "id"),
    ("the nw-550 won't pair", "nw550-pair", "id"),
    ("nw 500 pairing", "nw500-pair", "id"),
    ("shipping to Europe", "ship-eu", "meaning"),
    ("password reset", "acct-pw", "meaning"),
    ("damaged cup refund", "mug-dmg", "meaning"),
]
WEIGHTS = (0.0, 0.25, 0.5, 0.75, 1.0)


def recall_by_type(split, k=1, **kw):
    out = {}
    for q, want, typ in split:
        h, n = out.get(typ, (0, 0))
        out[typ] = (h + (want in search(q, **kw)[:k]), n + 1)
    return out


def total(r):
    return sum(h for h, _ in r.values())


def tune(split=DEV, k=1, lane=True):
    """Pick the weight with the best dev recall@k; ties go to the first (lowest) weight."""
    return max(WEIGHTS, key=lambda w: (total(recall_by_type(split, k, w=w, lane=lane)), -w))

"""Chapter 13: Search and Retrieval: Finding the Right Passage.

keyword_score() is a TOY word-overlap score, a simplified stand-in for BM25 (the usual
keyword ranking). meaning_score() uses the toy embed() from Chapter 12. Real systems use a
search library and a trained embedding model; the ideas are the same.
"""
import re

from ch12 import cosine
from stub_model import embed
from store import HANDBOOK

STOP = {"a", "an", "the", "i", "my", "me", "can", "do", "you", "is", "it", "of", "for",
        "to", "in", "on", "and", "or", "what", "how", "get", "your", "be", "with", "if"}


def words(text):
    return [w for w in re.findall(r"[a-z0-9-]+", text.lower()) if w not in STOP]


# MM-035: keywords match exact words; meaning matches ideas
def keyword_score(question, passage):
    q = set(words(question))
    return len(q & set(words(passage))) / len(q) if q else 0.0


def meaning_score(question, passage):
    a, b = embed(question), embed(passage)
    if not any(a) or not any(b):          # no known concept: the toy map has no point
        return 0.0
    return cosine(a, b)


def search(question, score, docs=HANDBOOK, k=3, floor=0.0):
    ranked = sorted(((score(question, t), cid) for cid, t in docs.items()), reverse=True)
    return [(cid, round(s, 2)) for s, cid in ranked[:k] if s > 0 and s >= floor]


# Hybrid: run both, then merge the two rankings (reciprocal rank fusion)
def hybrid(question, docs=HANDBOOK, k=3, kw_floor=0.5, mean_floor=0.6):
    fused = {}
    for score, floor in ((keyword_score, kw_floor), (meaning_score, mean_floor)):
        for rank, (cid, s) in enumerate(search(question, score, docs, k=len(docs), floor=floor)):
            fused[cid] = fused.get(cid, 0) + 1 / (60 + rank)
    return sorted(fused, key=fused.get, reverse=True)[:k]   # MM-037: may be empty


# MM-036: the top-k net, measured on labelled questions (question -> passages that answer it)
SEARCH_GOLDEN = [
    ("Can I get my money back for an unused lamp?", {"R1"}),
    ("Is the clearance jacket refundable? It was final-sale.", {"R3"}),
    ("My NW-500 battery stopped charging", {"S2"}),
    ("Where is my parcel?", {"S1"}),
    ("Can I swap a gift card for cash?", {"S4"}),
    ("I live in the EU, can I withdraw from my purchase?", {"S5"}),
    ("My mug arrived cracked. Refund, and who pays return shipping?", {"R2", "S3"}),
    ("The headphones cost INR 12,500 and arrived broken. Refund?", {"R2", "R4"}),
]


def recall_precision(k):
    """Recall: share of the needed passages that came back. Precision: share of what came
    back that was needed. No floor here, so k alone sets the size of the net."""
    needed = found = returned = 0
    for q, want in SEARCH_GOLDEN:
        got = hybrid(q, k=k, kw_floor=0, mean_floor=0)
        needed, found, returned = needed + len(want), found + len(want & set(got)), returned + len(got)
    return found / needed, found / returned


if __name__ == "__main__":
    for q in ("Can I get my money back?", "My NW-500 battery stopped charging"):
        print(q)
        print("  keyword:", search(q, keyword_score), "| meaning:", search(q, meaning_score))
        print("  hybrid :", hybrid(q))
    for k in (1, 2, 3, 5):
        r, p = recall_precision(k)
        print(f"k={k}: recall {r:.0%}, precision {p:.0%}")
    print("gift wrap? ->", hybrid("Do you sell gift wrap?"), "(nothing close enough)")

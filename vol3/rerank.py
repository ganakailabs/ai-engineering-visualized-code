"""Two-stage retrieval: retrieve wide and cheap, rerank to 5 (Vol 3 Ch 8).

First stage: the Ch 6 toy embedder gram-v1 over 40 fictional chunks. Second stage: a reranker that
reads the question and each chunk together. The stub reranker is a DEMONSTRATION: a
scripted scorer (phrase overlap after light word folding), not a model. An optional
real cross-encoder runs with AIEV_RERANKER (see vol3/runs/README.md); its numbers are
model experiments and stay [TO MEASURE] until run.
"""
import os
import re

import _root  # noqa: F401

import vectors as V

CHUNKS = {
    "ret-window": "Most items can be sent back within 30 days of delivery for a full refund.",
    "ret-label": "Print the return label from your order page and attach it to the box.",
    "ret-courier": "Return parcels are collected by the courier within a two day window.",
    "ret-final": "Final sale items cannot be returned or refunded.",
    "ret-gift": "Returned gifts are refunded as store credit to the gift giver.",
    "ret-damaged": "Damaged items: send a photo within 7 days and we refund the item.",
    "ret-status": "Track your return status from the returns page.",
    "ret-intl": "International returns take longer: allow 21 days for the parcel to arrive.",
    "lamp-window": "The desk lamp clamps to a window sill or a desk edge up to 5 cm thick.",
    "lamp-bulb": "The desk lamp takes one E27 bulb, sold separately.",
    "lamp-return": "Lamp shades are fragile; return them in the original packaging.",
    "nw500-batt": "NW-500 battery replacement is free within the 12-month warranty.",
    "nw550-batt": "NW-550 battery replacement is a paid service.",
    "nw500-pair": "To pair the NW-500, hold the power button until the light flashes blue.",
    "nw550-pair": "To pair the NW-550, open the app and choose add device.",
    "nw500-reset": "Reset the NW-500 by holding the power button for 10 seconds.",
    "nw-window": "The NW headphones pairing window stays open for 2 minutes.",
    "nw-return": "Opened headphones can be returned only if they are faulty.",
    "mug-care": "The mug set is dishwasher safe and microwave safe.",
    "mug-dmg": "A mug that arrives broken is refunded once we see a photo.",
    "mug-days": "Mug orders ship within 2 days.",
    "ship-in": "Standard delivery in India takes 3 to 5 days.",
    "ship-eu": "Delivery to the EU takes 7 to 10 days.",
    "ship-express": "Express delivery arrives the next day in metro cities.",
    "ship-track": "Track your parcel with the link in the dispatch email.",
    "ship-delay": "If delivery is late by more than 5 days, contact support.",
    "pay-cod": "Cash on delivery is available for orders under Rs 10,000.",
    "pay-emi": "EMI is available on cards for orders over Rs 3,000.",
    "pay-refund": "Refunds reach the original payment method in 5 to 7 days.",
    "pay-fail": "If a payment fails, any amount taken is reversed within 3 days.",
    "acct-pw": "Reset your password from the login page.",
    "acct-delete": "Ask support to delete your account; it takes 30 days.",
    "acct-email": "Change your email address in account settings.",
    "gift-card": "Gift cards can be exchanged for store credit, not cash.",
    "gift-expiry": "Gift cards expire 12 months after purchase.",
    "jacket-size": "The clearance jacket runs one size small.",
    "jacket-sale": "The clearance jacket is final sale.",
    "store-hours": "Support answers chats from 9 am to 9 pm, every day.",
    "store-window": "The shop window display changes every 30 days.",
    "warranty-claim": "To claim warranty, send the order number and a photo of the fault.",
}
GOLDEN = [   # (question, expected chunk id)
    ("what is the return window", "ret-window"),
    ("how many days to return an item for a refund", "ret-window"),
    ("can I pay when the parcel arrives", "pay-cod"),
    ("what bulb does the lamp need", "lamp-bulb"),
    ("how do I pair my NW-550", "nw550-pair"),
    ("do gift cards run out", "gift-expiry"),
    ("my mug came broken", "mug-dmg"),
    ("when will my refund reach my card", "pay-refund"),
]
_VECS = {d: V.embed(t, "gram-v1") for d, t in CHUNKS.items()}   # the cheap first stage
STOP = {"a", "an", "the", "is", "do", "i", "my", "to", "of", "for", "can", "how", "what",
        "when", "will", "have", "it", "in", "and", "by", "with", "be", "are", "on"}
FOLD = {"returned": "back", "return": "back", "returns": "back", "came": "arrives",
        "arrive": "arrives", "broken": "broken", "covered": "free", "warranty": "free",
        "card": "method", "pay": "delivery", "parcel": "delivery", "arrives": "arrives",
        "expire": "out", "run": "out", "window": "days", "days": "days"}


def first_stage(q, k):
    qv = V.embed(q, "gram-v1")
    s = {d: V.dot(qv, v) for d, v in _VECS.items()}
    return sorted(CHUNKS, key=lambda d: (-s[d], d))[:k]


def _words(text):
    toks = [w for w in re.findall(r"[a-z0-9]+", text.lower().replace("nw-", "nw")) if w not in STOP]
    return [FOLD.get(w, w) for w in toks]


def stub_score(q, chunk):
    """DEMONSTRATION scorer: folded word overlap plus a bonus for each shared pair of
    adjacent words, read from question and chunk together. Not a trained model."""
    qw, cw = _words(q), _words(chunk)
    pairs = lambda ws: {tuple(ws[i:i + 2]) for i in range(len(ws) - 1)}
    return len(set(qw) & set(cw)) + 2 * len(pairs(qw) & pairs(cw))


def real_scorer(model):
    """Optional real cross-encoder (sentence-transformers). See vol3/runs/README.md."""
    from sentence_transformers import CrossEncoder
    ce = CrossEncoder(model)
    return lambda q, c: float(ce.predict([(q, c)])[0])


def scorer():
    m = os.environ.get("AIEV_RERANKER")
    return real_scorer(m) if m else stub_score


def rerank(q, ids, n=5, score=stub_score):
    return sorted(ids, key=lambda d: (-score(q, CHUNKS[d]), ids.index(d)))[:n]


def recall(k, n=5, reranked=True, score=stub_score):
    hits = 0
    for q, want in GOLDEN:
        pool = first_stage(q, k)
        top = rerank(q, pool, n, score) if reranked else pool[:n]
        hits += want in (top if reranked else pool)
    return hits, len(GOLDEN)

"""Context assembly: dedupe, order, label and budget an evidence pack (Vol 3 Ch 11).

The pack is what the model sees. Ordering is authority first, then retrieval score.
Citations in a reply are validated against the pack ids; anything else escalates.
Coverage per k is measured on held-out labelled questions over the Ch 8 chunks.
Token counts use Vol 1's PLACEHOLDER counter (one token per word or mark).
"""
import re

import _root  # noqa: F401

import llm
import rerank as R
from stub_model import rough_token_count

AUTHORITY = {"policy": 3, "manual": 2, "past_tickets": 1, "faq": 2}

# Eight precedence-checked passages for "can I return my jacket, and do I need a photo?"
EIGHT = [
    dict(id="R1@2026-09-15", source="policy", score=.81, text="Returns accepted within 30 days of delivery."),
    dict(id="faq-12", source="faq", score=.79, text="Returns are accepted within 30 days of delivery."),
    dict(id="email-tpl-3", source="faq", score=.77, text="Returns accepted within 30 days of delivery!"),
    dict(id="R2@2026-09-15", source="policy", score=.64, text="Damaged items need a photo sent within 7 days."),
    dict(id="R5@2026-01-01", source="policy", score=.58, text="Final sale items cannot be returned."),
    dict(id="jacket-sale", source="manual", score=.55, text="The clearance jacket is final sale."),
    dict(id="ret-label", source="manual", score=.52, text="Print the return label from your order page."),
    dict(id="R1@2026-06-01-copy", source="faq", score=.50, text="Returns accepted within 30 days of delivery."),
]


def _words(t):
    return set(re.findall(r"[a-z0-9]+", t.lower()))


def near_dupe(a, b, cut=0.8):
    wa, wb = _words(a), _words(b)
    return len(wa & wb) / len(wa | wb) >= cut


def assemble(passages, budget=60):
    """Returns (pack, stats). pack = [(label, passage)], highest authority first."""
    order = sorted(passages, key=lambda p: (-AUTHORITY[p["source"]], -p["score"], p["id"]))
    unique, dupes = [], 0
    for p in order:                                  # 1 dedupe first
        if any(near_dupe(p["text"], u["text"]) for u in unique):
            dupes += 1
        else:
            unique.append(p)
    kept, tokens = [], 0
    for p in unique:                                 # 2 then fill the budget
        cost = rough_token_count(p["text"]) + 4      # + label and id
        if tokens + cost > budget:
            break
        kept.append(p)
        tokens += cost
    pack = [(f"S{i}", p) for i, p in enumerate(kept, 1)]
    return pack, dict(n_in=len(passages), dupes=dupes, kept=len(pack), over=len(unique) - len(pack), tokens=tokens, budget=budget)


def render(pack):
    return "\n".join(f"[{lab}] ({p['id']}) {p['text']}" for lab, p in pack)


def validate_citations(reply, pack):
    """Every [Sn] in the reply must be a label in the pack. Returns (ok, cited, unknown)."""
    cited = re.findall(r"\[(S\d+)\]", reply)
    labels = {lab for lab, _ in pack}
    unknown = [c for c in cited if c not in labels]
    return (bool(cited) and not unknown), cited, unknown


# Held-out labelled questions over the Ch 8 chunks: (question, ids the answer needs).
HELD_OUT = [
    ("what is the return window", {"ret-window"}),
    ("my mug came broken, how do I get a refund", {"mug-dmg"}),
    ("is the clearance jacket returnable", {"jacket-sale", "ret-final"}),
    ("can I pay when the parcel arrives", {"pay-cod"}),
    ("when will my refund reach my card", {"pay-refund"}),
    ("how do I claim warranty on my NW-500 battery", {"warranty-claim", "nw500-batt"}),
]


def pack_for(q, k, budget=400):
    ids = R.rerank(q, R.first_stage(q, 20), k)
    passages = [dict(id=i, source="manual", score=1 - n / 100, text=R.CHUNKS[i]) for n, i in enumerate(ids)]
    return assemble(passages, budget)[0]


def coverage(k):
    hit = sum(need <= {p["id"] for _, p in pack_for(q, k)} for q, need in HELD_OUT)
    return hit, len(HELD_OUT)


SYSTEM = ("Answer only from the evidence pack. Cite every claim with its label, like [S1]. "
          'Reply as JSON: {"reply": "..."}')


def _stub_answer(payload):
    """DEMONSTRATION reply, not a model: cites the window and the final-sale clauses."""
    return {"reply": "The jacket is final sale [S4], and final sale items cannot be returned [S3]. "
                     "Other items: 30 days [S1]."}


def answer(question, pack):
    """Ask the model (stub by default), then validate citations. Returns (action, reply)."""

    reply, _ = llm.ask_json(SYSTEM, f"Question: {question}\n\n{render(pack)}", _stub_answer)
    text = (reply or {}).get("reply", "")
    ok, _, _ = validate_citations(text, pack)
    return ("send" if ok else "escalate"), text

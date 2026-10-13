"""Chapter 12: Embeddings: Meaning as Coordinates.

embed() in stub_model.py is a TOY: five hand-picked concept axes. A real embedding
model learns its own axes, hundreds or thousands of them, and you call it like a chat
model. The ideas (points, angles, nearest neighbours) are the same.
"""
import math

from stub_model import AXES, embed
from store import POLICY


# MM-032: similarity is the angle between two arrows (cosine)
def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


# MM-033: nearest neighbours. Rank every clause by cosine; keep the top k above a floor.
def nearest(question, docs=POLICY, k=2, floor=0.6):
    q = embed(question)
    ranked = sorted(((cosine(q, embed(t)), cid) for cid, t in docs.items()), reverse=True)
    return [(cid, round(s, 2)) for s, cid in ranked[:k] if s >= floor]


if __name__ == "__main__":
    print("two arrows (3, 4) and (4, 3): cosine =", round(cosine((3, 4), (4, 3)), 2))
    print("axes:", AXES)
    print("'money back' ->", [round(x, 2) for x in embed("Can I get my money back?")])
    print("'refund'     ->", [round(x, 2) for x in embed("Is a refund possible?")])
    print("broken mug, money back:", nearest("My mug arrived broken, can I get my money back?"))
    print("parcel tracking:", nearest("Where is my parcel?"))
    # MM-034: close is not correct. The toy, like real models, barely sees "not".
    yes, no = "Final-sale items can be refunded.", "Final-sale items cannot be refunded."
    print("can vs cannot:", round(cosine(embed(yes), embed(no)), 2))

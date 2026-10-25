"""Chapter 14: Chunking: Cutting Documents So the Right Piece Is Found."""
import re

from ch13 import hybrid
from store import HANDBOOK, HANDBOOK_TEXT, REGION


# MM-038 / MM-039: fixed-size chunks of `size` words; each starts `size - overlap` words on
def chunk(text, size=12, overlap=0):
    w = text.split()
    step = size - overlap
    starts = [i for i in range(0, len(w), step)
              if i == 0 or i + overlap < len(w)]
    return {f"C{n + 1}": " ".join(w[i:i + size])
            for n, i in enumerate(starts)}


# Sidebar: cut at sentence ends instead of word counts
def sentence_chunks(text):
    parts = re.split(r"(?<=\.)\s+", text)
    return {f"C{n + 1}": p for n, p in enumerate(parts)}


# MM-040: labels on every chunk; filter on the label first, then rank what is left
def search_labelled(question, region, k=2):
    allowed = {cid: t for cid, t in HANDBOOK.items()
               if REGION[cid] in ("ALL", region)}
    return hybrid(question, docs=allowed, k=k, kw_floor=0, mean_floor=0)


def top_chunk(question, chunks):
    got = hybrid(question, docs=chunks, k=1, kw_floor=0, mean_floor=0)
    return chunks[got[0]] if got else None


if __name__ == "__main__":
    q = "Is a final-sale jacket refundable?"
    for size, overlap in ((4, 0), (12, 0), (12, 4), (120, 0)):
        chunks = chunk(HANDBOOK_TEXT, size, overlap)
        print(f"size {size:>3}, overlap {overlap}: {len(chunks):>2} chunks -> {top_chunk(q, chunks)!r}")
    print("sentence chunks:", len(sentence_chunks(HANDBOOK_TEXT)), "->",
          top_chunk(q, sentence_chunks(HANDBOOK_TEXT)))
    w = "Can I withdraw from my purchase within 14 days?"
    print("India ticket, no filter :", hybrid(w, k=2, kw_floor=0, mean_floor=0))
    print("India ticket, region=IN :", search_labelled(w, "IN"))

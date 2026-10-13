"""Chapter 14 exercise: cut the handbook four ways.

1. Chunk the handbook at 12 words with no overlap and with 4 words of overlap. Search
   "Is a final-sale jacket refundable?" in each. Which top chunk holds the whole rule?
2. Cut it at sentence ends instead. How many chunks, and what comes back?
3. Search "Can I withdraw from my purchase within 14 days?" for an EU and an India customer.
Run: python3 solutions/ch14_solution.py
"""
import _path  # noqa: F401
from ch14 import chunk, search_labelled, sentence_chunks, top_chunk
from store import HANDBOOK_TEXT

if __name__ == "__main__":
    q = "Is a final-sale jacket refundable?"
    plain = top_chunk(q, chunk(HANDBOOK_TEXT, 12, 0))
    overlapped = top_chunk(q, chunk(HANDBOOK_TEXT, 12, 4))
    sentences = sentence_chunks(HANDBOOK_TEXT)
    by_sentence = top_chunk(q, sentences)
    print("12/0:", plain, "\n12/4:", overlapped, f"\nsentences ({len(sentences)}):", by_sentence)
    w = "Can I withdraw from my purchase within 14 days?"
    eu, india = search_labelled(w, "EU"), search_labelled(w, "IN")
    print("EU:", eu, "| India:", india)
    rule = "Final-sale items cannot be refunded."
    assert rule not in plain and rule in overlapped, "overlap keeps the rule whole"
    assert by_sentence == rule and len(sentences) == 12
    assert "S5" in eu and "S5" not in india, "the label stops an EU rule answering an India ticket"
    print("ch14 solution: OK")

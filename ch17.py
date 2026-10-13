"""Chapter 17: Is the RAG Working? Evaluating Retrieval and Answers."""
import re

from ch13 import words
from ch15 import augment, generate, index, retrieve

# MM-046: one golden set, two scorecards. Each question lists the passages that answer it.
RAG_GOLDEN = [
    ("Can I get my money back for an unused lamp?", {"R1"}),
    ("Is the clearance jacket refundable? It was final-sale.", {"R3"}),
    ("My NW-500 battery stopped charging", {"S2"}),
    ("Where is my parcel?", {"S1"}),
    ("Can I swap a gift card for cash?", {"S4"}),
    ("Who pays return shipping for a broken mug?", {"S3"}),
]


# MM-047: did we fetch it? recall@k = share of questions whose passage is in the top k
def fetched(question, want, k=3):
    return want <= set(retrieve(question, index(), k))


# MM-048: did it stick to the source? Every sentence must be backed by a cited passage.
def unsupported(reply, passages):
    if reply.startswith("escalate"):
        return []
    cited = re.findall(r"\[(\w+)\]", reply)
    said = set()
    for c in cited:
        said |= set(words(passages.get(c, "")))
    body = re.sub(r"\[\w+\]|^answer:", "", reply)
    out = []
    for sentence in re.split(r"(?<=\.)\s+", body.strip()):
        claim = set(words(sentence))
        if claim and len(claim & said) < len(claim) / 2:
            out.append(sentence)
    return out


def scorecards(k=3):
    rows = []
    for q, want in RAG_GOLDEN:
        passages = retrieve(q, index(), k)
        reply = generate(augment(passages), q)
        rows.append((q, fetched(q, want, k), not unsupported(reply, passages), reply))
    search = sum(r[1] for r in rows) / len(rows)
    answers = sum(r[2] for r in rows) / len(rows)
    return search, answers, rows


if __name__ == "__main__":
    search, answers, rows = scorecards()
    print(f"search scorecard (recall@3): {search:.0%}   answer scorecard (faithful): {answers:.0%}")
    for q, got, faithful, reply in rows:
        if not (got and faithful):
            print(f"- {q}\n  fetched={got} faithful={faithful}: {reply}")

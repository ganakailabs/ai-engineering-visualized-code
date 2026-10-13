"""Chapter 15: The RAG Pipeline: Retrieve, Then Answer."""
from ch13 import hybrid
from stub_model import call_model
from store import HANDBOOK

RULES = ("You answer customer questions for Northwind Goods. Answer only from the passages "
         "below. Cite the passage id in square brackets. If the passages do not answer the "
         "question, reply 'escalate: <what is missing>'.")


# MM-042: four stages, each one a place to look when an answer is wrong
def index(docs=HANDBOOK):                       # 1. index: the pages you can search
    return dict(docs)


def retrieve(question, idx, k=3, **floors):     # 2. retrieve: top k above the floors
    return {cid: idx[cid] for cid in hybrid(question, docs=idx, k=k, **floors)}


def augment(passages, rules=RULES):             # 3. augment: put the pages in the prompt
    return rules + "\nPASSAGES:\n" + "\n".join(f"[{cid}] {t}" for cid, t in passages.items())


def generate(system, question):                 # 4. generate: the model answers
    return call_model([{"role": "system", "content": system},
                       {"role": "user", "content": question}])["text"]


def rag(question, idx=None, k=3):
    idx = idx or index()
    passages = retrieve(question, idx, k)
    return generate(augment(passages), question), list(passages)


# MM-041: the same question, closed book (no pages) and open book (with pages)
def closed_book(question):
    return generate("You answer customer questions for Northwind Goods. Closed book.", question)


if __name__ == "__main__":
    q = "My NW-500 battery stopped charging. Is it covered?"
    print("closed book:", closed_book(q))
    print("open book  :", rag(q))
    print("tracking   :", rag("Where is my parcel?"))
    print("gift wrap  :", rag("Do you sell gift wrap?"))

"""Chapter 16: Grounded Answers: Citations and "I Don't Know".

Extends Chapter 7's citation gate (MM-019) from policy clauses to retrieved passages."""
import re

from ch13 import words
from ch15 import augment, generate, index, retrieve

CITE_ONLY = "Answer from the passages below. Cite the passage id in square brackets."


# MM-044: answers with receipts. Every claim points at a passage id.
def receipts(reply):
    return re.findall(r"\[(\w+)\]", reply)


# Chapter 7's gate, extended: the cited passage must be one we retrieved, and must say it
def passage_gate(reply, passages):
    if reply.startswith("escalate"):
        return True, "abstained"
    cited = receipts(reply)
    if not cited:
        return False, "no receipt"
    if any(c not in passages for c in cited):
        return False, "cites a passage we did not retrieve"
    text = re.sub(r"\[\w+\]|^answer:", "", reply)
    claim = set(words(text)) - {"yes", "we"}
    said = set().union(*(words(passages[c]) for c in cited))
    if len(claim & said) < len(claim) / 2:
        return False, "the cited passage does not say this"
    if negated(text) != any(negated(passages[c])
                            for c in cited):
        return False, "the claim flips a negation"
    return True, "ok"


# Word overlap cannot see meaning: "can be refunded" and "cannot be refunded"
# share almost every word. This toy polarity check catches a flipped negation.
# It still misses other contradictions (numbers, dates, swapped subjects) and can
# reject a correct paraphrase. Real systems need a claim-by-claim support check.
NEGATIONS = {"not", "no", "never", "cannot", "can't", "won't", "isn't", "don't"}


def negated(text):
    return bool(NEGATIONS & set(text.lower().replace(".", " ").split()))


# MM-045: the honest abstain is a designed outcome, not an error
ABSTAIN = "escalate: I can't find this in our policy, so I'm passing you to a colleague."


def grounded(question, rules=None, k=3):
    passages = retrieve(question, index(), k)
    if not passages:                                   # nothing close enough (Chapter 13)
        return ABSTAIN, "no passage above the floor"
    reply = generate(augment(passages, rules) if rules else augment(passages), question)
    ok, why = passage_gate(reply, passages)
    return (reply if ok else ABSTAIN), why


if __name__ == "__main__":
    q = "Do you price match if I find it cheaper?"
    passages = retrieve(q, index())
    loose = generate(augment(passages, CITE_ONLY), q)
    print("retrieved :", list(passages))
    print("cite only :", loose, "| receipts:", receipts(loose))
    print("gate      :", passage_gate(loose, passages))
    print("grounded  :", grounded(q, rules=CITE_ONLY))
    print("full rules:", grounded(q))
    print("battery   :", grounded("My NW-500 battery stopped charging. Is it covered?"))
    r3 = {"R3": "Final-sale items cannot be refunded."}
    flipped = "answer: Final-sale items can be refunded [R3]."
    print("flipped   :", passage_gate(flipped, r3))

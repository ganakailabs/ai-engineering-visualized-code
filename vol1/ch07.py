"""Chapter 7: Fluent Is Not True: Hallucination."""
import re

from parse import decision_reply
from stub_model import call_model
from store import POLICY, policy_text

QUESTION = "Do you do price match refunds?"  # the policy has no price-match clause

# MM-019: give the facts, and make "I can't answer from this" an allowed answer
GROUNDED = ("Answer only from the policy below. If the policy does not cover the "
            "question, reply 'escalate: <what is missing>'.\n" + policy_text())


# MM-017: a fluent answer must point at a clause that exists
def cited_clauses_exist(text):
    cited = re.findall(r"\b(R\d+)\b", text)
    return bool(cited) and all(c in POLICY for c in cited)


def citation_gate(reply):
    """Decisions must cite a real clause; anything else goes to a person."""
    reply = decision_reply(reply) or reply    # '<Approve> ...' -> 'approve: ...'
    decision = reply.split(":", 1)[0].strip().lower()
    if decision in ("approve", "deny") and not cited_clauses_exist(reply):
        return "escalate: held by the citation gate (no real clause cited)"
    return reply


def ask(system, question=QUESTION):
    return call_model([{"role": "system", "content": system},
                       {"role": "user", "content": question}])["text"]


if __name__ == "__main__":
    plain = ask(policy_text())
    print("policy only     :", plain, "| cited clauses exist:", cited_clauses_exist(plain))
    print("after the gate  :", citation_gate(plain))
    grounded = ask(GROUNDED)
    print("answer from page:", grounded)
    print("after the gate  :", citation_gate(grounded))

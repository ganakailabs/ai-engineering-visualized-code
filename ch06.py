"""Chapter 6: Inside the Context Window: What the Model Pays Attention To."""
from collections import Counter

from ch02 import order_facts
from ch05 import softmax
from store import fetch_order, policy_text
from ollama_model import selected
from parse import DECISIONS, label
from stub_model import call_model

# MM-014: ONE attention head, ONE query, as a toy. Chapter 5 used softmax to turn
# next-token scores into odds; here the same function turns query-key MATCH scores
# into attention shares over the window (one head's 100%). Scores are made up;
# a real model learns them, per token, per head, per layer, looking back only.
QUESTION = "is order #4410 refundable?"
LABELS = {"R3 final-sale clause": 3.0, "R1 30-day clause": 1.5, "greeting": 0.2}
EMAIL_SCORE = 1.0  # each quoted "still waiting on #4410" email matches a little


def attention_shares(labels, n_emails=0):
    window = dict(labels)
    for i in range(n_emails):
        window[f"email {i + 1}"] = EMAIL_SCORE
    return softmax(window, 1.0)


# MM-016: a position test you can run on YOUR model
def position_test_prompts(key_clause, filler_docs, question):
    """Same content, key clause moved to start, middle and end."""
    out = {}
    for where in ("start", "middle", "end"):
        docs = list(filler_docs)
        idx = {"start": 0, "middle": len(docs) // 2, "end": len(docs)}[where]
        docs.insert(idx, key_clause)
        out[where] = "\n\n".join(docs) + "\n\nQUESTION: " + question
    return out


# MM-016: the position test as a small eval. Same tickets, same text, only the
# order facts move. Count the decisions at each position.
HELD_OUT = ["Refund for my jacket, order #4410?", "Refund for order #1234?",
            "Refund for my mug set, order #2001?", "Refund for #3100, please."]
FILLER = [f"Thread email {i}: still waiting, any news?" for i in range(10)]


def position_eval(tickets=HELD_OUT, model=call_model):
    counts = {}
    for ticket in tickets:
        oid = ticket.split("#")[1][:4]
        facts = order_facts(oid, fetch_order(oid))
        for where, text in position_test_prompts(facts, FILLER, ticket).items():
            system = ("Reply as '<approve|deny|escalate>: <reason>'.\n"
                      + policy_text() + "\n\n" + text)
            r = model([{"role": "system", "content": system},
                       {"role": "user", "content": ticket}])
            decision = label(r["text"], DECISIONS) or "unparsed"
            counts.setdefault(where, Counter())[decision] += 1
    return counts


if __name__ == "__main__":
    for n in (0, 5, 20):
        shares = attention_shares(LABELS, n)
        print(f"{n:>2} emails in the window -> R3 gets {shares['R3 final-sale clause']:.0%}")
    prompts = position_test_prompts("[R3] Final-sale items cannot be refunded.",
                                    [f"Thread email {i}: ..." for i in range(10)],
                                    "Order #4410 was final sale. Refund?")
    print({k: v.index("[R3]") for k, v in prompts.items()})
    for where, c in position_eval().items():
        print(f"position eval, facts at {where:6}: {dict(sorted(c.items()))}")
    if selected():
        print(f"(real model {selected()}: compare the rows; a difference is the finding)")
    else:
        print("(the stub is position-blind, so the counts match; rerun with a real model)")

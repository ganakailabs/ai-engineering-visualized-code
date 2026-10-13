"""Chapter 6: Inside the Context Window: What the Model Pays Attention To."""
from ch05 import softmax

# MM-014: attention in miniature. One token brings a question (query); every other piece
# of the window shows a label (key); match scores become shares that add up to 100%.
# Scores are made up for the demo; a real model learns them, per token, per head.
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


if __name__ == "__main__":
    for n in (0, 5, 20):
        shares = attention_shares(LABELS, n)
        print(f"{n:>2} emails in the window -> R3 gets {shares['R3 final-sale clause']:.0%}")
    prompts = position_test_prompts("[R3] Final-sale items cannot be refunded.",
                                    [f"Thread email {i}: ..." for i in range(10)],
                                    "Order #4410 was final sale. Refund?")
    print({k: v.index("[R3]") for k, v in prompts.items()})

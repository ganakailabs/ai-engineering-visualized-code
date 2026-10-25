"""Chapter 4: Tokens: What the Model Reads and What You Pay."""
from collections import Counter

from stub_model import call_model, rough_token_count
from store import policy_text

# Check current pricing on your provider's pricing page. Never hard-code from a book.
PRICE_PER_MILLION = {"input": None, "output": None}
# MADE-UP example rates, in toy units per million tokens, only to show the arithmetic.
EXAMPLE_RATES = {"input": 1.0, "output": 4.0}


# MM-009: byte-pair encoding in miniature: merge the most frequent pair, repeat
def merge_pair(w, a, b):
    i = 0
    while i < len(w) - 1:
        if (w[i], w[i + 1]) == (a, b):
            w[i:i + 2] = [a + b]
        i += 1


def toy_bpe(words, merges):
    pieces = [list(w) for w in words]       # single letters
    for _ in range(merges):
        pairs = Counter(p for w in pieces for p in zip(w, w[1:]))
        if not pairs:
            break
        a, b = pairs.most_common(1)[0][0]    # commonest neighbours
        for w in pieces:
            merge_pair(w, a, b)              # glue them: one token
    return pieces


# MM-009 + MM-010: read the meter on every call, keep input and output apart
def log_usage(result, log):
    u = result["usage"]
    log.append({"input_tokens": u["input_tokens"], "output_tokens": u["output_tokens"],
                "finish_reason": result["finish_reason"]})


def cost(entry, prices=PRICE_PER_MILLION):
    if None in prices.values():
        return None  # unknown until you fill in today's prices
    return (entry["input_tokens"] * prices["input"]
            + entry["output_tokens"] * prices["output"]) / 1_000_000


# MM-011: pack the suitcase by priority, reserve room for the answer
def pack_context(rules, policy, history, ticket, window, reserve_output, notes=""):
    budget = window - reserve_output
    must = [{"role": "system", "content": rules + "\n" + policy + "\nCASE NOTES: " + notes},
            {"role": "user", "content": ticket}]
    used = sum(rough_token_count(m["content"]) for m in must)
    if used > budget:
        raise ValueError("rules + policy + ticket alone do not fit: shorten them")
    kept = []
    for turn in reversed(history):  # newest first
        t = rough_token_count(turn["content"])
        if used + t > budget:
            break
        kept.insert(0, turn)
        used += t
    dropped = len(history) - len(kept)
    return [must[0]] + kept + [must[1]], used, dropped


if __name__ == "__main__":
    words = ["refund", "refunds", "refunded", "fund", "funds"]
    for n in (0, 3, 6):
        print(f"BPE after {n} merges:", ["|".join(w) for w in toy_bpe(words, n)])
    rules = "You decide refund requests. Reply as '<approve|deny|escalate>: <reason>'."
    log = []
    log_usage(call_model([{"role": "system", "content": rules + policy_text()},
                          {"role": "user", "content": "Refund for #1234?"}]), log)
    print(log[-1], "cost:", cost(log[-1]))   # None: real prices not filled in
    print("cost at made-up example rates:", cost(log[-1], EXAMPLE_RATES), "toy units",
          "| x 10,000 tickets:", round(cost(log[-1], EXAMPLE_RATES) * 10_000, 2))

    # a long thread: 40 back-and-forth turns of pasted emails
    history = []
    for i in range(40):
        history.append({"role": "user", "content": f"Email {i}: still waiting on order #1234, see thread below. " * 3})
        history.append({"role": "assistant", "content": "Sorry for the wait. Checking now."})
    msgs, used, dropped = pack_context(rules, policy_text(), history,
                                       "So, refund for it or not?", window=2000, reserve_output=300,
                                       notes="order_id=1234; customer asked for refund on turn 1")
    print("messages sent:", len(msgs), "tokens used:", used, "turns dropped:", dropped)

    capped = call_model([{"role": "user", "content": "Refund for #1234?"}], max_output_tokens=5)
    print("capped:", capped["finish_reason"], "|", capped["text"])

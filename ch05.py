"""Chapter 5: One Token at a Time: Why Answers Vary."""
import math
import random
from collections import Counter

from stub_model import call_model, sample
from store import policy_text

# MM-012: a toy next-token step. Scores are made up for the demo.
SCORES = {"approve": 1.0, "escalate": 0.8, "deny": 0.6}


def softmax(scores, temperature):
    """Scores -> probabilities. Lower temperature sharpens, higher flattens."""
    exps = {k: math.exp(v / temperature) for k, v in scores.items()}
    total = sum(exps.values())
    return {k: e / total for k, e in exps.items()}


def roll(temperature, n=20, seed=7):
    rng = random.Random(seed)
    return Counter(sample(SCORES, temperature, rng) for _ in range(n))


def same_ticket_n_times(ticket, n=5, temperature=1.0):
    msgs = [{"role": "system", "content": policy_text()}, {"role": "user", "content": ticket}]
    return [call_model(msgs, temperature=temperature, seed=i)["text"].split(":")[0] for i in range(n)]


# MM-013: top-p keeps the most likely tokens until their probabilities add up to p
def top_p(probs, p):
    keep, total = {}, 0.0
    for k, v in sorted(probs.items(), key=lambda kv: -kv[1]):
        keep[k] = v
        total += v
        if total >= p:
            break
    return keep


if __name__ == "__main__":
    for t in (0.2, 1.0, 1.5):
        print(f"T={t}:", {k: f"{v:.0%}" for k, v in softmax(SCORES, t).items()})
    for t in (0.0, 0.5, 1.0, 2.0):
        print("20 rolls at temperature", t, dict(roll(t)))
    print("top-p 0.6 at T=1.0 keeps:", list(top_p(softmax(SCORES, 1.0), 0.6)))
    ticket = "I opened the box but never used it. Refund?"
    print("same ticket x5 at 1.0:", same_ticket_n_times(ticket))
    print("same ticket x5 at 0.0:", same_ticket_n_times(ticket, temperature=0.0))

"""Chapter 21: Memory: What the Agent Remembers."""
from datetime import date

from stub_model import rough_token_count
from store import TODAY
from ch13 import keyword_score, search

# MM-056: long-term memory is a store your code writes and reads.
# (The scratchpad is just the messages list inside one task: Ch 19.)
NOTES = [
    {"who": "asha", "day": date(2026, 10, 2), "consent": True,
     "text": "Mug set #2001 arrived cracked; a replacement was sent."},
    {"who": "asha", "day": date(2026, 9, 12), "consent": True,
     "text": "Prefers email, not phone calls."},
    {"who": "asha", "day": date(2026, 4, 20), "consent": True,
     "text": "Asked about the NW-500 headphones warranty."},
    {"who": "ravi", "day": date(2026, 9, 30), "consent": True,
     "text": "Clearance jacket #4410 refund was denied (R3)."},
]
for i in range(36):                     # past routine tickets, for scale
    NOTES.append({"who": "asha", "day": date(2026, 6 + i % 4, 1 + i % 28),
                  "consent": True,
                  "text": f"Routine order #{7000 + i} delivered."})


# MM-058: what to forget. No consent, no note; old notes expire.
KEEP_DAYS = 90


def remember(who, text, consent, day=TODAY):
    if not consent:
        return False
    NOTES.append({"who": who, "day": day, "consent": True,
                  "text": text})
    return True


def forget(today=TODAY):
    kept = [n for n in NOTES if (today - n["day"]).days <= KEEP_DAYS]
    dropped = len(NOTES) - len(kept)
    NOTES[:] = kept
    return dropped


# MM-057: remember by search (Part III, reused)
def recall(who, question, k=2):
    mine = {str(i): n["text"] for i, n in enumerate(NOTES)
            if n["who"] == who}
    hits = search(question, keyword_score, mine, k=k, floor=0.2)
    return [mine[i] for i, _ in hits]


def tokens(notes):
    return rough_token_count(" ".join(notes))


if __name__ == "__main__":
    q = "My new mug set arrived cracked again"
    every = [n["text"] for n in NOTES if n["who"] == "asha"]
    print(f"stuff every note: notes={len(every)}, tokens={tokens(every)}")
    found = recall("asha", q)
    print(f"recall by search: notes={len(found)}, tokens={tokens(found)}")
    for n in found:
        print("  -", n)
    print("no consent stored?", remember("asha", "Lives alone.", False))
    print("forgotten (older than 90 days):", forget())
    print("warranty note still there?",
          any("warranty" in n["text"] for n in NOTES))

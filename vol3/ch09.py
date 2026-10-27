"""Chapter 9: Query Understanding: Rewrite, Route and Decompose.

Run from the repo root:  python3 vol3/ch09.py
Real model (optional):  AIEV_MODEL=ollama:llama3.2 python3 vol3/ch09.py
The default rewriter is a scripted stub. The meaning-kept check and the router are
plain code and run the same on either.
"""
import _root  # noqa: F401

import query as Q

HISTORY = {"product": "NW-500", "order": "3100"}


def show(message, history):
    print(f'  "{message}"')
    for kind, detail in Q.understand(message, history):
        if kind == "check":
            print("    check   " + " ".join(f"{k} kept={'yes' if v else 'NO'}" for k, v in detail.items()))
        elif kind == "route":
            print(f"    route   part={detail[0]} source={detail[1]}")
        else:
            print(f"    {kind:7} {detail}")


if __name__ == "__main__":
    print("Part 1 (MM-081): rewrite from ticket history, then check the meaning")
    show("It broke again, and can I return the charger too, but not the case?", HISTORY)
    print("\n  a rewrite that dropped the exclusion:")
    bad = ["can I return the NW-500 charger and case?"]
    kept = Q.meaning_kept("can I return the charger too, but not the case?", bad)
    print(f"    {bad} -> " + " ".join(f"{k}={'yes' if v else 'NO'}" for k, v in kept.items()))

    print("\nPart 2 (MM-082): pass through, route, or ask")
    show("how do I reset the NW-550", {})
    show("is it still covered?", {})

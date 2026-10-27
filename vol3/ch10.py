"""Chapter 10: When Sources Disagree: Authority, Applicability and Abstain.

Run from the repo root:  python3 vol3/ch10.py
Four named conflicts, one per step of precedence(), then per-source abstain floors
chosen on the dev split and reported on held-out. No model is used.
"""
import _root  # noqa: F401

import precedence as P


def run(name, ids):
    kept, dropped, esc = P.precedence(ids)
    print(f"  {name}:")
    for i, why in dropped:
        print(f"    precedence dropped={i} reason={why}")
    if esc:
        print("    escalate conflict=unresolved")
    for i in kept:
        print(f"    precedence kept={i}  cite {P.cite(i)}")


if __name__ == "__main__":
    print("Part 1 (MM-083): one conflict per step")
    run("applicability", ["R1@2026-09-15", "R1@2026-11-01", "R1-EU@2026-01-01"])
    run("authority", ["R1@2026-09-15", "ticket-8812"])
    run("recency among peers", ["R1@2026-06-01", "R1@2026-09-15"])
    run("unresolved", ["M7@2026-08-01a", "M7@2026-08-01b"])

    print("\nPart 2 (MM-084): abstain floors per source, chosen on dev")
    floors = {s: P.calibrate(s) for s in P.SCORES}
    for s, f in floors.items():
        d, h = P.outcome(P.SCORES[s]["dev"], f), P.outcome(P.SCORES[s]["held"], f)
        print(f"  {s:12} floor={f:.2f}  dev right={d[0]}/{d[1]}  held-out right={h[0]}/{h[1]}")
    for s, score in (("policy", 0.66), ("past_tickets", 0.79)):
        verdict = "below floor" if P.abstain(s, score, floors) else "answer"
        print(f"  abstain source={s} score={score} {verdict}" if verdict != "answer"
              else f"  use     source={s} score={score}")

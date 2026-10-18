"""Chapter 5 exercise: load the dice, then pin the decision down.

1. Print the softmax table for SCORES at temperatures 0.2, 1.0 and 1.5.
2. Send the borderline ticket five times at 1.0 and five times at 0.0 and count the
   distinct decisions.
Run: python3 solutions/ch05_solution.py
"""
import _path  # noqa: F401  (adds code/support-assistant/ to the import path)
from ch05 import SCORES, softmax, same_ticket_n_times, top_p

TICKET = "I opened the box but never used it. Refund?"

if __name__ == "__main__":
    table = {t: softmax(SCORES, t) for t in (0.2, 1.0, 1.5)}
    print("token     " + "".join(f"T={t:<6}" for t in table))
    for tok in SCORES:
        print(f"{tok:<10}" + "".join(f"{table[t][tok]:<8.0%}" for t in table))
    hot, cold = same_ticket_n_times(TICKET, temperature=1.0), same_ticket_n_times(TICKET, temperature=0.0)
    print("distinct at 1.0:", sorted(set(hot)), "| distinct at 0.0:", sorted(set(cold)))
    # self-test (run_solutions.py relies on these)
    assert round(table[0.2]["approve"], 2) == 0.67 and round(table[1.0]["approve"], 2) == 0.40
    assert all(abs(sum(p.values()) - 1) < 1e-9 for p in table.values()), "probabilities add to 100%"
    assert len(set(hot)) > 1 and len(set(cold)) == 1
    assert list(top_p(table[1.0], 0.6)) == ["approve", "escalate"]
    greedy = softmax(SCORES, 0)          # T <= 0: greedy, no division by zero
    assert greedy[max(SCORES, key=SCORES.get)] == 1.0 and sum(greedy.values()) == 1.0
    print("ch05 solution: OK")

"""Chapter 6 exercise: watch attention dilute, then build a position test.

1. Print R3's attention share with 0, 5 and 20 quoted emails in the window, and check
   that every window's shares add up to 100%.
2. Build the start/middle/end prompts and check they hold exactly the same text.
Run: python3 solutions/ch06_solution.py
"""
import _path  # noqa: F401  (adds code/support-assistant/ to the import path)
from ch06 import LABELS, attention_shares, position_test_prompts

if __name__ == "__main__":
    r3 = {}
    for n in (0, 5, 20):
        shares = attention_shares(LABELS, n)
        assert abs(sum(shares.values()) - 1) < 1e-9, "shares add up to 100%"
        r3[n] = shares["R3 final-sale clause"]
        print(f"{n:>2} emails: R3 {r3[n]:.0%}")
    prompts = position_test_prompts("[R3] Final-sale items cannot be refunded.",
                                    [f"Thread email {i}: ..." for i in range(10)],
                                    "Order #4410 was final sale. Refund?")
    words = {k: sorted(v.split()) for k, v in prompts.items()}
    print({k: v.index("[R3]") for k, v in prompts.items()})
    # self-test (run_solutions.py relies on these)
    assert r3[0] > r3[5] > r3[20], "more competing text, smaller share for R3"
    assert round(r3[0], 2) == 0.78 and round(r3[20], 2) == 0.25
    assert words["start"] == words["middle"] == words["end"], "same text, only the position moves"
    print("ch06 solution: OK")

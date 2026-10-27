"""Chapter 15 exercise: swap the order.

Swap the two candidate replies for the ten judge cases.
Predict first: how many verdicts flip? On the stub the lean is scripted, so the
count is a demonstration; a real judge's count is a model experiment.
"""
import _path  # noqa: F401

import metrics as M

before = M.judge_pairs()
after = M.judge_pairs(swap=True)
flipped = [M.PAIRS[i][0] for i, (a, b) in enumerate(zip(before, after)) if a != b]
print(f"flips {len(flipped)}/10: {flipped}")
assert flipped == ["EU withdrawal"]
always_first = lambda q, a, b: "first"     # noqa: E731
print(f"always-first judge: agreement {M.agreement(always_first)}, "
      f"flips {M.flips(always_first)}/10")
assert M.flips(always_first) == 10 and not M.trusted(always_first, bar=0.8)

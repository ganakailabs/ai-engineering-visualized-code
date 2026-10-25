"""Chapter 9 exercise: move the bar, watch the pick change.

Run the bake-off once, then pick a model at bars of 75%, 90% and 95%. Work out how many
times dearer the toy reasoning model is per resolved ticket than the toy large model,
and which tickets the toy small model fails.
Run: python3 vol1/solutions/ch09_solution.py
"""
import _path  # noqa: F401  (adds vol1/ to the import path)
from _path import STUB, DECISIONS  # noqa: F401
from ch08 import GOLDEN, passes
from ch09 import assistant, bake_off, pick

if __name__ == "__main__":
    rows = bake_off()
    picks = {bar: pick(rows, bar) for bar in (0.75, 0.90, 0.95)}
    for bar, m in picks.items():
        print(f"bar {bar:.0%}: pick {m}")
    ratio = rows["stub-reasoning"]["cost_per_resolved"] / rows["stub-large"]["cost_per_resolved"]
    print(f"reasoning vs large, cost per resolved ticket: {ratio:.1f}x")
    small_fails = [t for t, oid, exp in GOLDEN if not passes(assistant(t, oid, "stub-small")[0], exp)]
    print("small model fails:", small_fails)
    # self-test (run_solutions.py relies on these)
    assert all(m is None or m in rows for m in picks.values()), "pick a measured model, or none"
    assert all(r["resolved"] <= len(GOLDEN) for r in rows.values())
    if STUB:
        assert picks == {0.75: "stub-small", 0.90: "stub-large", 0.95: None}
        assert ratio > 3, "thinking tokens are billed, and the easy tickets did not need them"
        assert sum("#3100" in t for t in small_fails) == 3, "the R4 amount check is where small slips"
        # resolutions and handoffs are counted apart: a correct escalate is not a resolution
        assert {m: r["resolved"] for m, r in rows.items()} == dict.fromkeys(rows, 9)
        assert rows["stub-small"]["handoffs"] < rows["stub-large"]["handoffs"], \
            "small 'resolves' #3100 by approving it: fewer handoffs, wrong answers"
    print("ch09 solution: OK")

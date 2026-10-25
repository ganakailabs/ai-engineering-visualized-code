"""Chapter 17 exercise: read both scorecards, fix the right half.

1. Run scorecards() and list which questions fail search and which fail the answer check.
2. The lamp question fails search. Lower the meaning floor to 0.55 and check it again.
3. Which sentence in the return-shipping answer has no source?
Run: python3 vol1/solutions/ch17_solution.py
"""
import _path  # noqa: F401
from _path import STUB, DECISIONS  # noqa: F401
from ch15 import augment, generate, index, retrieve
from ch17 import fetched, passage_recall, scorecards, unsupported

if __name__ == "__main__":
    search, answers, rows = scorecards()
    print(f"search {search:.0%}, answers {answers:.0%}")
    lamp = "Can I get my money back for an unused lamp?"
    before = list(retrieve(lamp, index()))
    after = list(retrieve(lamp, index(), mean_floor=0.55))
    fixed = generate(augment(retrieve(lamp, index(), mean_floor=0.55)), lamp)
    print("lamp, floor 0.6:", before, "| floor 0.55:", after, "->", fixed)
    q = "Who pays return shipping for a broken mug?"
    p = retrieve(q, index())
    extra = unsupported(generate(augment(p), q), p)
    print("unsupported:", extra)
    assert 0 <= search <= 1 and 0 <= answers <= 1
    assert set(before) <= set(after), "a lower floor only adds passages"
    assert isinstance(extra, list)
    if STUB:
        assert round(search, 2) == 0.83 and round(answers, 2) == 0.83
        assert "R1" not in before and "R1" in after and "[R1]" in fixed
        assert extra == ["We also refund the original delivery fee."]
    two = "Can I get my money back for an unused lamp, and who pays return shipping?"
    rec, ok = passage_recall(two, {"R1", "S3"}), fetched(two, {"R1", "S3"})
    print("two passages: recall", rec, "all-evidence success", ok)
    assert 0 <= rec <= 1 and (ok is False or rec == 1)
    if STUB:
        assert rec == 0.5 and ok is False
    print("ch17 solution: OK")

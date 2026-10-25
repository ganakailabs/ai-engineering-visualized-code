"""Chapter 12 exercise: turn the two knobs, then fool the map.

1. Check the arrows: cosine of (3, 4) and (4, 3) is 0.96; of (1, 0) and (0, 1) is 0.
2. Search "Where is my parcel?" with the floor at 0.5 and at 0.6. Which floor stops a
   refund clause from being handed to a tracking question?
3. Show that "can be refunded" and "cannot be refunded" land on the same point.
Run: python3 vol1/solutions/ch12_solution.py
"""
import _path  # noqa: F401  (adds vol1/ to the import path)
from _path import STUB, DECISIONS  # noqa: F401
from ch12 import cosine, nearest
from stub_model import embed

if __name__ == "__main__":
    arrows = round(cosine((3, 4), (4, 3)), 2), round(cosine((1, 0), (0, 1)), 2)
    print("arrows:", arrows)
    low, high = nearest("Where is my parcel?", floor=0.5), nearest("Where is my parcel?", floor=0.6)
    print("parcel, floor 0.5:", low, "| floor 0.6:", high)
    mug = nearest("My mug arrived broken, can I get my money back?", k=1)
    print("broken mug, k=1:", mug)
    same = cosine(embed("Final-sale items can be refunded."), embed("Final-sale items cannot be refunded."))
    print(f"can vs cannot: {same:.2f}")
    # self-test (run_solutions.py relies on these)
    assert arrows == (0.96, 0.0)
    assert all(s >= 0.5 for _, s in low) and all(s >= 0.6 for _, s in high), "the floor holds"
    assert len(high) <= len(low) and len(mug) <= 1 and -1.0 <= same <= 1.01
    if STUB:
        assert low and low[0][0] == "R1" and high == [], "the higher floor returns nothing close enough"
        assert mug[0][0] == "R2"
        assert round(same, 2) == 1.0, "close is not correct: the meaning map ignores 'not'"
    print("ch12 solution: OK")

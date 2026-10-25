"""Chapter 13 exercise: size the net, then draw the line.

1. Print recall and precision for k = 1, 3 and 5 on SEARCH_GOLDEN. Which k finds every
   needed passage, and what does it cost in junk?
2. Search "Do you sell gift wrap?" with the floors off and on. What comes back each time?
3. Search "My NW-500 battery stopped charging" by keywords only and by meaning only.
Run: python3 vol1/solutions/ch13_solution.py
"""
import _path  # noqa: F401
from _path import STUB, DECISIONS  # noqa: F401
from ch13 import hybrid, keyword_score, meaning_score, recall_precision, search

if __name__ == "__main__":
    table = {k: recall_precision(k) for k in (1, 3, 5)}
    for k, (r, p) in table.items():
        print(f"k={k}: recall {r:.0%}, precision {p:.0%}")
    off = hybrid("Do you sell gift wrap?", kw_floor=0, mean_floor=0)
    on = hybrid("Do you sell gift wrap?")
    print("gift wrap, floors off:", off, "| floors on:", on)
    q = "My NW-500 battery stopped charging"
    kw, mean = search(q, keyword_score), search(q, meaning_score)
    print("NW-500, keywords:", kw, "| meaning:", mean)
    assert all(0 <= r <= 1 and 0 <= p <= 1 for r, p in table.values())
    assert table[1][0] <= table[3][0] <= table[5][0], "a wider net never finds less"
    assert set(on) <= set(off), "a floor only removes matches"
    assert kw[0][0] == "S2", "keywords find a model number"
    if STUB:
        assert table[1][0] < 1.0 and table[3][0] == 1.0, "k=3 is the smallest net that finds every passage"
        assert table[5][1] < table[3][1], "a wider net brings more junk"
        assert off == ["S4"] and on == [], "the floor turns a junk match into 'nothing close enough'"
        assert mean == [], "the toy meaning map has no axis for a model number"
    print("ch13 solution: OK")

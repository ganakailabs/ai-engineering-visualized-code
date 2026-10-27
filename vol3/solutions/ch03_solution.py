"""Chapter 3 exercise: add a row to the warranty table and check it survives parsing.

Add a Switzerland row (CH, 24 months, store) to the fixture's table, then check its cells
on both parses: the layout-aware chunks and the naive 10-word cut. Compare cells with
their column names, not whole strings.
"""
import copy

import _path  # noqa: F401

import layout as L

doc = copy.deepcopy(L.load())
table = next(b for b in doc["pages"][1]["blocks"] if b["type"] == "table")
row = ["CH", "24 months", "store"]
table["rows"].append(row)

r = L.run(doc, echo=False)
layout_texts = [c["text"] for c in r["chunks"]]
naive_texts = L.fixed_chunks(L.naive_text(doc))
assert L.cell_check(layout_texts, table["header"], row)
assert not L.cell_check(naive_texts, table["header"], row)
assert r["spotcheck"] == (3, 3)
hit = next(c for c in r["chunks"] if "Region: CH" in c["text"])
assert hit["page"] == 2 and hit["kind"] == "row"
print(f"layout: {hit['id']} cells kept=yes")
print("naive:  cells kept=no")
print("ch03 solution: OK")

"""Chapter 3: table rows stay records, footers go, low OCR confidence is flagged."""
import copy

import _path  # noqa: F401

import layout as L

DOC = L.load()


def test_rows_are_records_with_column_names():
    r = L.run(DOC, echo=False)
    rows = [c for c in r["chunks"] if c["kind"] == "row"]
    assert len(rows) == 3
    assert L.cell_check([c["text"] for c in rows], ["Region", "Warranty"], ["EU", "24 months"])


def test_break_naive_cut_loses_the_row():
    flat = L.fixed_chunks(L.naive_text(DOC))
    assert not L.cell_check(flat, ["Region", "Warranty"], ["EU", "24 months"])


def test_footers_dropped_and_columns_in_order():
    els = L.parse(DOC)
    assert not any("page 1" in e["text"] for e in els)
    p1 = [e["text"] for e in els if e["page"] == 1 and e["kind"] == "text"]
    assert p1[0].startswith("Keep your receipt.") and p1[0].endswith("your order.")


def test_low_confidence_ocr_flagged_and_floor_matters():
    assert [e["page"] for e in L.parse(DOC) if e.get("flagged")] == [5]
    assert not any(e.get("flagged") for e in L.parse(DOC, floor=0.5))


def test_spotcheck_fails_when_a_cell_moves():
    doc = copy.deepcopy(DOC)
    doc["pages"][1]["blocks"][1]["rows"][1][1] = "12 months"     # EU cell wrong
    assert L.spotcheck(doc, L.parse(doc)) == (2, 3)


def test_chunk_ids_are_stable_per_page():
    a = [c["id"] for c in L.run(DOC, echo=False)["chunks"]]
    doc = copy.deepcopy(DOC)
    doc["pages"][3]["blocks"].insert(0, {"type": "text", "col": 1, "line": 0, "text": "New."})
    b = [c["id"] for c in L.run(doc, echo=False)["chunks"]]
    assert [i for i in a if ":p2." in i] == [i for i in b if ":p2." in i]


def test_real_parser_rows_match_when_installed():
    try:
        import pdfplumber
    except ImportError:
        return                                   # optional dependency
    with pdfplumber.open(L.FIXTURE.with_suffix(".pdf")) as pdf:
        rows = pdf.pages[1].extract_tables()[0]
    assert rows[2] == ["EU", "24 months", "email or store"]


def test_short_row_goes_to_manual_review_not_the_index():
    # A14: zip() would silently drop the missing cell; the row is held instead
    doc = copy.deepcopy(DOC)
    table = next(b for b in doc["pages"][1]["blocks"] if b["type"] == "table")
    table["rows"].append(["US", "12 months"])
    r = L.run(doc, echo=False)
    assert [e["text"] for e in r["elements"] if e["kind"] == "review"] == \
        ["manual review: row 4 missing Claim by"]
    assert not any("Region: US" in c["text"] for c in r["chunks"])
    assert r["spotcheck"] == (3, 3)


if __name__ == "__main__":
    from _run import run_all
    run_all("test_layout")

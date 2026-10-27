"""Chapter 4: heading chunks, parent expansion, and the applicability gate."""
from datetime import date

import _path  # noqa: F401

import chunking as C

META, BODY = C.read()
PARENTS = C.section_chunks(META, BODY)


def test_break_fixed_cut_splits_r2():
    cuts = C.fixed_chunks(BODY)
    assert not any("7 days" in c and "photo" in c for c in cuts)


def test_heading_chunk_keeps_r2_whole_and_parent_is_returned():
    r = C.answer_context("My mug arrived broken. What do I need to send?", "mug", "IN",
                         echo=False)
    assert r["hit"]["parent"] == r["parent"]["id"]
    assert "7 days" in r["parent"]["text"] and "photo" in r["parent"]["text"]


def test_missing_tag_is_not_applicable():
    ok, why = C.applies({"product": "ALL", "region": "ALL"}, "mug", "IN")
    assert not ok and "tag missing" in why


def test_effective_date_against_question_date():
    h1 = next(p for p in PARENTS if p["title"].startswith("H1"))
    assert not C.applies(h1["tags"], "mug", "IN")[0]
    assert C.applies(h1["tags"], "mug", "IN", date(2026, 11, 1))[0]


def test_region_and_product_are_applicability():
    s5 = next(p for p in PARENTS if p["title"].startswith("S5"))
    assert C.applies(s5["tags"], "mug", "EU")[0] and not C.applies(s5["tags"], "mug", "IN")[0]
    kept = [p["id"].split(":")[1] for p in C.gate(PARENTS, "mug", "IN")]
    assert kept == ["R1", "R2", "R3"]


def test_overlap_costs_words_and_still_cuts_by_count():
    meta, body = C.read()
    a, b = C.fixed_chunks(body, 12, 0), C.fixed_chunks(body, 12, 6)
    assert len(b) > len(a) and sum(map(len, b)) > sum(map(len, a))
    assert not any("7 days" in c and "photo" in c for c in b)


if __name__ == "__main__":
    from _run import run_all
    run_all("test_chunking")

"""Chapter 11: dedupe, budget, ordering, citation validation, held-out coverage."""
import _path  # noqa: F401

import assemble as A


def test_duplicates_removed_and_budget_kept():
    pack, s = A.assemble(A.EIGHT)
    assert s["dupes"] == 3 and s["kept"] == 4 and s["tokens"] <= s["budget"]
    texts = [p["text"] for _, p in pack]
    assert sum("30 days" in t for t in texts) == 1


def test_authority_orders_before_score():
    pack, _ = A.assemble(A.EIGHT)
    assert [p["source"] for _, p in pack][:3] == ["policy"] * 3


def test_phantom_citation_rejected():
    pack, _ = A.assemble(A.EIGHT)
    ok, _, unknown = A.validate_citations("30 days [S1], photo optional [S7].", pack)
    assert not ok and unknown == ["S7"]
    assert A.validate_citations("no citations at all", pack)[0] is False


def test_stub_reply_cites_only_pack():
    pack, _ = A.assemble(A.EIGHT)
    action, reply = A.answer("jacket?", pack)
    assert action == "send" and A.validate_citations(reply, pack)[1] == ["S4", "S3", "S1"]


def test_coverage_measured_not_assumed():
    assert A.coverage(2) == (3, 6) and A.coverage(10) == (4, 6)


def test_contradictory_passages_never_merged():
    # External review probe: Jaccard 0.8, opposite meaning.
    a = "Final sale items can be returned."
    b = "Final sale items cannot be returned."
    assert not A.near_dupe(a, b)
    ps = [dict(id="a", source="policy", score=.9, text=a),
          dict(id="b", source="policy", score=.8, text=b)]
    pack, s = A.assemble(ps, budget=100)
    assert s["dupes"] == 0 and [p["id"] for _, p in pack] == ["a", "b"]


def test_numbers_and_products_block_merge():
    assert not A.near_dupe("Returns accepted within 30 days of delivery.",
                           "Returns accepted within 15 days of delivery.")
    assert not A.near_dupe("The NW-500 charger is part of the NW-500 Travel Bundle.",
                           "The NW-500 case is part of the NW-500 Travel Bundle.")
    assert not A.near_dupe("Returns accepted within 30 days of delivery.",
                           "Returns accepted only within 30 days of delivery.")


def test_filler_only_difference_still_merges():
    assert A.near_dupe("Returns accepted within 30 days of delivery.",
                       "Returns are accepted within 30 days of delivery.")


def test_budget_stop_keeps_priority_prefix():
    ps = [dict(id="big", source="policy", score=.9, text="word " * 50),
          dict(id="small", source="faq", score=.8, text="Short fact.")]
    pack, s = A.assemble(ps, budget=30)
    assert pack == [] and s["first_over"] == "big" and s["over"] == 2


def test_budget_skip_policy_fills_past_oversized():
    ps = [dict(id="big", source="policy", score=.9, text="word " * 50),
          dict(id="small", source="faq", score=.8, text="Short fact.")]
    pack, s = A.assemble(ps, budget=30, on_over="skip")
    assert [p["id"] for _, p in pack] == ["small"] and s["first_over"] == "big"


def test_unknown_budget_policy_rejected():
    try:
        A.assemble(A.EIGHT, on_over="drop")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


if __name__ == "__main__":
    from _run import run_all
    run_all("test_assemble")

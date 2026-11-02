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


def _pair(a, b):
    return [dict(id="a", source="policy", score=.9, text=a),
            dict(id="b", source="policy", score=.8, text=b)]


def test_contradictory_passages_never_merged():
    a = "Final sale items can be returned."
    b = "Final sale items cannot be returned."
    assert not A.same_passage(dict(id="a", text=a), dict(id="b", text=b))
    pack, s = A.assemble(_pair(a, b), budget=100)
    assert s["dupes"] == 0 and [p["id"] for _, p in pack] == ["a", "b"]


def test_swapped_windows_never_merged():
    # A36: the same words in a different order are a different rule
    a = "Refund window 30 days; warranty window 90 days."
    b = "Refund window 90 days; warranty window 30 days."
    assert not A.same_passage(dict(id="a", text=a), dict(id="b", text=b))
    assert A.assemble(_pair(a, b), budget=100)[1]["dupes"] == 0


def test_numbers_products_and_rewording_block_merge():
    for a, b in [("Returns accepted within 30 days of delivery.",
                  "Returns accepted within 15 days of delivery."),
                 ("The NW-500 charger is part of the NW-500 Travel Bundle.",
                  "The NW-500 case is part of the NW-500 Travel Bundle."),
                 ("Returns accepted within 30 days of delivery.",
                  "Returns are accepted within 30 days of delivery.")]:   # reworded: kept
        assert not A.same_passage(dict(id="a", text=a), dict(id="b", text=b))


def test_exact_copies_merge():
    assert A.same_passage(dict(id="x", text="one"), dict(id="x", text="two"))      # same id
    assert A.same_passage(dict(id="a", text="Returns accepted within 30 days of delivery."),
                          dict(id="b", text="returns accepted within 30 days of delivery"))


def test_non_text_reply_escalates():
    # A38: only {"reply": non-empty str} is sent
    import llm
    pack, _ = A.assemble(A.EIGHT)
    real = llm.ask_json
    for bad in (42, [], None, {}, {"reply": 7}, {"reply": ""}):
        llm.ask_json = lambda *a, _bad=bad, **k: (_bad, repr(_bad))
        try:
            assert A.answer("jacket?", pack) == ("escalate", ""), bad
        finally:
            llm.ask_json = real


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

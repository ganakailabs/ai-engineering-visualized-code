"""Chapter 7: identifier normalizer, exact lane, tuning on dev, report on held-out."""
import _path  # noqa: F401

import hybrid as H


def test_normalize_id_cases():
    for text in ("NW-500", "nw500", "nw 500", "Nw-500 battery"):
        assert H.normalize_id(text) == ["NW-500"], text
    assert H.normalize_id("order 2001") == []
    assert H.analyze("nw500") == ["nw500"]          # the plain analyzer keeps it glued


def test_exact_lane_finds_glued_code():
    hits, ids = H.exact_lane("nw500")
    assert ids == ["NW-500"] and hits == ["nw500-batt", "nw500-pair"]
    assert H.search("nw500", "words", lane=False)[0] not in hits


def test_rrf_uses_ranks_only():
    assert H.rrf([["a", "b"], ["b", "a"]]) == ["a", "b"]   # tie broken by id
    assert H.rrf([["a", "b"], ["b", "c"]])[0] == "b"


def test_weight_chosen_on_dev_reported_on_held_out():
    w = H.tune()
    assert w == 0.5
    assert H.recall_by_type(H.DEV, w=w) == {"id": (3, 3), "meaning": (3, 3)}
    assert H.recall_by_type(H.HELD_OUT, w=w) == {"id": (2, 3), "meaning": (3, 3)}


def test_two_product_ids_need_a_chunk_naming_both():
    # A23: the lane asks for chunks that carry EVERY id in the query; none names both
    # products here, so the lane is empty and the fused order alone decides
    hits, ids = H.exact_lane("Is the NW-500 or the NW-550 battery better?")
    assert ids == ["NW-500", "NW-550"] and hits == []
    assert H.search("Is the NW-500 or the NW-550 battery better?")[:2] == ["nw500-batt", "nw550-batt"]


def test_unknown_id_gets_no_lane_and_a_wrong_product_on_top():
    # A23: NW-999 is in no chunk; the lane is empty and the top hit is another product,
    # so the caller must check the id before answering ("unknown product"), not trust rank 1
    hits, ids = H.exact_lane("How do I reset the NW-999?")
    assert ids == ["NW-999"] and hits == []
    top = H.search("How do I reset the NW-999?")[0]
    assert top == "nw550-pair" and "NW-999" not in H.DOC_IDS[top]


if __name__ == "__main__":
    from _run import run_all
    run_all("test_hybrid")

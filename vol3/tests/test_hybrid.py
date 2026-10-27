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


if __name__ == "__main__":
    from _run import run_all
    run_all("test_hybrid")

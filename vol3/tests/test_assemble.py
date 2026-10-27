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


if __name__ == "__main__":
    from _run import run_all
    run_all("test_assemble")

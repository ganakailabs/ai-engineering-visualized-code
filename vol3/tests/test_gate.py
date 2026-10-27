"""Chapter 16: review, split, paired interval and the regression gate."""
import _path  # noqa: F401

import gate as G


def test_review_rejects_ungrounded_leaking_and_duplicates():
    ok, bad = G.review()
    reasons = sorted(r for _, r in bad)
    assert len(ok) == 8 and reasons == ["answer not in passage", "near-duplicate",
                                        "near-duplicate", "question gives away the answer"]


def test_split_is_stable():
    ok, _ = G.review()
    assert G.split(ok) == G.split(list(ok)) and len(G.split(ok)[1]) == 3


def test_critical_failure_blocks_despite_higher_mean():
    g = G.gate("baseline", "chunking_change")
    assert g["verdict"] == "blocked" and g["critical"] == ["eu-withdrawal"]
    assert g["diff"] > 0


def test_abstain_everything_fails():
    g = G.gate("baseline", "abstain_all")
    assert g["verdict"] == "blocked" and g["answered"] == 0
    assert any("answered 0/13" in r for r in g["reasons"])


def test_fixed_change_passes_but_is_not_called_a_win():
    g = G.gate("baseline", "chunking_fixed")
    assert g["verdict"] == "pass" and not g["win"] and g["interval"][0] <= 0


def test_paired_interval_reproducible():
    b, n = G.results("baseline"), G.results("chunking_fixed")
    assert G.paired_interval(b, n) == G.paired_interval(b, n)


if __name__ == "__main__":
    from _run import run_all
    run_all("test_gate")

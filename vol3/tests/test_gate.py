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


def _perfect():
    return {c: (True, not a) for c, _, a, _ in G.BENCH}


def test_new_noncritical_failures_block():
    # Review probe: perfect baseline, two new noncritical failures. The old gate
    # passed this (no critical failure, answer rate still above 80%).
    base, new = _perfect(), _perfect()
    new["in-battery-row"] = (False, False)
    new["bundle-stand"] = (False, False)
    g = G.gate_results(base, new)
    assert g["verdict"] == "blocked" and not g["critical"]
    assert sorted(g["new_failures"]) == ["bundle-stand", "in-battery-row"]
    assert g["diff"] == -0.125
    # with a declared tolerance of two, the same records pass, labelled honestly
    g2 = G.gate_results(base, new, max_new_failures=2)
    assert g2["verdict"] == "pass" and g2["label"].startswith("pass within tolerance (2 new")


def test_missing_case_blocks_not_passes():
    base, new = _perfect(), _perfect()
    del new["retired-clause"]
    g = G.gate_results(base, new)
    assert g["verdict"] == "blocked" and g["missing"] == ["retired-clause"]


def test_label_never_claims_improvement_when_interval_touches_zero():
    g = G.gate("baseline", "chunking_fixed")
    assert g["label"] == "pass, no regression found (improvement not demonstrated)"


def test_scripted_verdicts_unchanged():
    assert G.gate("baseline", "chunking_change")["verdict"] == "blocked"
    assert G.gate("baseline", "abstain_all")["verdict"] == "blocked"
    assert G.gate("baseline", "no_precedence")["verdict"] == "blocked"
    assert G.gate("baseline", "chunking_fixed")["new_failures"] == []


if __name__ == "__main__":
    from _run import run_all
    run_all("test_gate")

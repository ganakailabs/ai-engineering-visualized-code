"""Chapter 15: every code metric against hand-computed cases, ablation, judge check."""
import _path  # noqa: F401

import metrics as M


def close(a, b):
    return abs(a - b) < 1e-9


def test_retrieval_metrics_by_hand():
    r, rel = ["a", "x", "b", "y"], {"a", "b"}
    assert close(M.recall_at_k(r, rel, 2), 0.5)
    assert close(M.precision_at_k(r, rel, 2), 0.5)
    assert close(M.rr(r, rel), 1.0) and close(M.rr(["x", "a"], rel), 0.5)
    assert close(M.ndcg_at_k(["a", "b"], rel, 2), 1.0)
    assert M.ndcg_at_k(["x", "a"], {"a"}, 2) < 1.0
    assert M.hit_rate([(r, rel), (["x"], {"z"})], 3) == 0.5


def test_edge_cases_no_relevant_and_empty():
    assert M.recall_at_k(["a"], set(), 5) == 0.0
    assert M.rr(["a"], set()) == 0.0 and M.ndcg_at_k(["a"], set(), 5) == 0.0
    assert M.context_precision([], {"a"}) == 0.0
    assert M.context_recall(["a"], set()) == 1.0
    assert M.citation_accuracy([], {"a"}) == 0.0


def test_abstain_split_and_abstain_everything():
    rows = [(False, True), (True, True), (True, False)]
    assert M.abstain_rates(rows) == (1, 1, 1, 2)
    allx = [(ok, True) for ok, _ in rows]
    ca, cn, fa, an = M.abstain_rates(allx)
    assert ca == cn and fa == an      # perfect on one, fails the other


def test_scorecard_values():
    s = M.scorecard()
    assert s["correct"] == 3 and s["n"] == 8
    assert s["abstain"] == (1, 2, 3, 6)
    assert round(s["precision"], 2) == 0.23 and round(s["mrr"], 2) == 0.75


def test_ablation_names_rerank_not_lowest_number():
    stage, gains = M.limiting_stage()
    assert stage == "rerank" and gains == {"retrieve": 0, "rerank": 2, "answer": 1}
    assert M.end_score(("retrieve", "rerank")) == 6


def test_judge_checked_before_trust():
    assert M.agreement() == (6, 10) and M.flips() == 1
    assert not M.trusted()
    always_first = lambda q, a, b: "first"     # noqa: E731
    assert M.agreement(always_first) == (8, 10) and M.flips(always_first) == 10
    assert not M.trusted(always_first, bar=0.8)


if __name__ == "__main__":
    from _run import run_all
    run_all("test_metrics")

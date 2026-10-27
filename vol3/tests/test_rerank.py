"""Chapter 8: two-stage funnel and the recall ceiling."""
import _path  # noqa: F401

import rerank as R


def test_rerank_cannot_beat_the_net():
    for k in (5, 10, 20, 30, 40):
        assert R.recall(k)[0] <= R.recall(k, reranked=False)[0]


def test_numbers_in_chapter():
    assert R.recall(5, reranked=False) == (4, 8)
    assert [R.recall(k)[0] for k in (5, 10, 20, 30, 40)] == [4, 6, 7, 7, 7]
    q = "what is the return window"
    assert R.first_stage(q, 40).index("ret-window") == 15
    assert "ret-window" in R.rerank(q, R.first_stage(q, 20))


def test_rerank_only_reorders():
    pool = R.first_stage("do gift cards run out", 10)
    assert set(R.rerank("do gift cards run out", pool, 10)) == set(pool)


if __name__ == "__main__":
    from _run import run_all
    run_all("test_rerank")

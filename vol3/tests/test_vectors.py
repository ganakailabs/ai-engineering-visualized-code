"""Chapter 6: contract refusal, ANN recall and work counts, embedder comparison."""
import _path  # noqa: F401

import vectors as V

IX = V.ClusteredIndex()
QS = [q for q, _ in V.GOLDEN]


def test_contract_mismatch_refused():
    for change in ({"version": "v2"}, {"dim": 128}, {"normalized": False}):
        c = {**V.contract(), **change}
        try:
            IX.query("x", c)
        except ValueError:
            continue
        raise AssertionError(f"accepted {change}")
    assert IX.check(V.contract()) == []


def test_ann_recall_counts():
    found, total, compared, routing, missed = V.ann_recall(IX, QS, k=1, probe=1)
    assert (found, total, compared) == (5, 6, 20)
    # Review probe: candidates scored leave out the centroid comparisons.
    assert routing == len(QS) * len(IX.centroids) == 24
    assert missed == [("pair my NW-550", "nw550-pair")]
    assert V.ann_recall(IX, QS, k=1, probe=len(IX.groups))[0] == 6


def test_embedders_on_the_golden_set():
    assert V.recall_at("lexi-v1", 1) == (3, 6)
    assert V.recall_at("gram-v1", 1) == (4, 6)


def test_vectors_are_normalized():
    v = V.embed("NW-500")
    assert abs(V.dot(v, v) - 1.0) < 1e-9


if __name__ == "__main__":
    from _run import run_all
    run_all("test_vectors")

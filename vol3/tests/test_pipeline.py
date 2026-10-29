"""Connected capstone: each stage reads the previous stage's output."""
import _path  # noqa: F401

import pipeline as PL

P = PL.Pipeline()


def test_index_is_checked_before_it_serves():
    assert P.built["chunks"] == len(P.rows) and P.built["ocr_held"] == 1
    assert P.check == {"orphans": 0, "stale": 0, "missing": 0, "mixed": False}
    assert not P.vectors.check(PL.V.contract(PL.MODEL))      # Ch 6 contract matches


def test_demo_ticket_flows_through_three_paths():
    out = P.answer(PL.DEMO, PL.ASHA)
    assert [r["path"] for r in out["parts"]] == ["documents", "records", "graph"]
    doc = out["parts"][0]
    assert "b-note.1" in doc["trail"]["access_dropped"]          # Ch 5 at search
    assert doc["trail"]["reranked"][0] == "handbook-returns@2026-09-15:R2"
    # the pack holds only what the stages handed on, and every citation is in it
    handed = {e["id"] for r in out["parts"] for e in r["evidence"]}
    assert {p["id"] for _, p in out["pack"]} <= handed
    assert out["action"] == "send" and set(out["cited"]) <= handed
    assert "Your refund count in 2026 (your own records only): 1." in out["reply"]


def test_budget_counts_work_not_time():
    out = P.answer(PL.DEMO, PL.ASHA)
    c = out["budget"].counts
    assert c["bm25_docs_scored"] == len(P.rows)                  # BM25 scores every chunk
    assert 0 < c["vectors_scored"] < len(P.rows)                 # the clustered index opens a subset
    assert c["centroid_comparisons"] == len(PL.SEEDS)
    assert c["sql_queries"] == 1 and c["pack_tokens"] <= PL.LIMITS["pack_tokens"]
    assert not any("ms" in k or "time" in k or "cost" in k for k in c)


def test_over_budget_escalates():
    tight = PL.Pipeline(limits=dict(PL.LIMITS, reranker_pairs=3))
    out = tight.answer(PL.DEMO, PL.ASHA)
    assert out["action"] == "escalate" and any("over budget" in w for w in out["why"])


def test_unknown_coverage_and_conflict_escalate():
    assert P.answer("Is my NW-500 cable covered by the bundle warranty?", PL.ASHA)["action"] == "escalate"
    out = P.answer("When should I replace the NW-500 battery?", PL.ASHA)
    assert out["action"] == "escalate" and "disagree" in out["why"][0]
    loose = PL.Pipeline(use_precedence=False)
    assert loose.answer("When should I replace the NW-500 battery?", PL.ASHA)["action"] == "send"


def test_tickets_graded_by_code():
    r = PL.results(P)
    assert len(r) == len(PL.TICKETS)
    # the known failure: the stub reranker prefers "7 days" and the 30-day clause
    # never reaches the pack; the full pipeline sends a wrong answer here
    assert r["agent-7-days"] == (False, False)
    assert all(ok for c, (ok, _) in r.items() if c != "agent-7-days")


def test_gate_over_pipeline_output():
    g = PL.run_gate("full", "no_access_filter")
    assert g["verdict"] == "blocked" and "vip-photo" in g["critical"]
    g = PL.run_gate("full", "no_precedence")
    assert g["verdict"] == "blocked" and "battery-cycles" in g["new_failures"]


if __name__ == "__main__":
    from _run import run_all
    run_all("test_pipeline")

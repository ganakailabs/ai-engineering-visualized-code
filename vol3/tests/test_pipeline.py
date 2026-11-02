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


def _count_calls(monkey_limits):
    import llm
    calls = []
    real = llm.ask_json

    def counting(*a, **k):
        calls.append(a[0][:20])
        return real(*a, **k)
    llm.ask_json = counting
    try:
        out = PL.Pipeline(limits=dict(PL.LIMITS, **monkey_limits)).answer(PL.DEMO, PL.ASHA)
    finally:
        llm.ask_json = real
    return out, calls


def test_budget_refuses_before_the_call():
    # D1 / A55: a model call is reserved before it runs; limit 1 means exactly 1 call
    out, calls = _count_calls(dict(model_calls=1))
    assert len(calls) == 1 and out["budget"].counts["model_calls"] == 1
    assert out["action"] == "escalate" and "refused before it ran" in out["why"][0]
    out, calls = _count_calls({})
    assert len(calls) == out["budget"].counts["model_calls"] == 6      # counter == real calls


def test_reranker_budget_refuses_before_scoring():
    tight = PL.Pipeline(limits=dict(PL.LIMITS, reranker_pairs=3))
    out = tight.answer(PL.DEMO, PL.ASHA)
    assert out["budget"].counts.get("reranker_pairs", 0) == 0          # nothing was scored


def test_non_text_reply_escalates():
    # A38: a reply that is not a {"reply": str} object is never sent
    import llm
    real = llm.ask_json
    for bad in (42, [], None, {}, {"reply": 7}):
        def fake(system, user, stub, **k):
            if system == PL.AS.SYSTEM:
                return bad, repr(bad)
            return real(system, user, stub, **k)
        llm.ask_json = fake
        try:
            out = P.answer(PL.DEMO, PL.ASHA)
        finally:
            llm.ask_json = real
        assert out["action"] == "escalate" and "reply is not text" in out["why"], bad


def test_checks_passed_is_not_content_correctness():
    # A47: a false sentence with an in-pack label still passes the action/evidence checks
    real = PL._stub_reply
    PL._stub_reply = lambda payload: {"reply": "Every product has a lifetime warranty [S1]."}
    try:
        case = next(c for c in PL.TICKETS if c[0] == "return-window")
        (checks_passed, _), out = PL.grade(P, case)
    finally:
        PL._stub_reply = real
    assert out["action"] == "send" and checks_passed


def test_access_filter_runs_before_lanes_are_cut():
    # D4 / A20: another tenant's internal copies cannot starve the visible passage
    real = PL.corpus

    def crowded():
        rows, built = real()
        for src_id in ("a-ret.2", "handbook-returns@2026-09-15:R2"):
            for n in range(PL.K_LANE):
                rows[f"b-copy.{src_id}.{n}"] = dict(rows[src_id], tenant="b", audience="internal")
        return rows, dict(built, chunks=len(rows))
    PL.corpus = crowded
    try:
        p = PL.Pipeline()
    finally:
        PL.corpus = real
    q = "My mug arrived broken, do I need to send a photo for a refund?"
    unfiltered, _ = p.vectors.query(q, PL.V.contract(PL.MODEL), PL.K_LANE, probe=2)
    assert all(i.startswith("b-copy") for i in unfiltered)     # cut first: lane is all copies
    out = p.answer(q, PL.ASHA)
    packed = {x["id"] for _, x in out["pack"]}
    assert not any(i.startswith("b-") for i in packed)
    assert "handbook-returns@2026-09-15:R2" in packed and "a-ret.2" in packed


def test_capstone_repair_on_all_ten():
    # D7 / A56-A57: N_RERANK=3 alone swaps one failure for another; scoping the
    # tie-escalation to the family the part asks about fixes both, with no regression
    full = PL.results(PL.Pipeline(**PL.CONFIGS["full"]))
    n3 = PL.results(PL.Pipeline(**PL.CONFIGS["n3"]))
    fixed = PL.results(PL.Pipeline(**PL.CONFIGS["n3_scoped"]))
    assert sum(v[0] for v in full.values()) == sum(v[0] for v in n3.values()) == 9
    assert n3["agent-7-days"][0] and not n3["pair-nw500"][0]
    assert all(v[0] for v in fixed.values())
    # the battery question still escalates: there the tie IS the claim
    assert fixed["battery-cycles"] == (True, True)


if __name__ == "__main__":
    from _run import run_all
    run_all("test_pipeline")

"""Remaining Vol 3 real-model measurements, one log per chapter (see README.md).

    AIEV_MODEL=ollama:llama3.2 python3 vol3/runs/real_runs.py          # all six chapters
    AIEV_MODEL=ollama:llama3.2 python3 vol3/runs/real_runs.py ch16     # one chapter

Writes vol3/runs/<date>-<model>-chNN-real.txt for Ch 10, 11, 13, 14, 15 and 16, and
<date>-<model>-grading-sheet.csv for the Ch 11 and Ch 16 replies. Nothing that the
README says to grade by hand is graded here: those grade columns are left blank.
Embedders: AIEV_EMBED_A / AIEV_EMBED_B (default ollama:nomic-embed-text and
ollama:mxbai-embed-large when AIEV_MODEL is set, the toy gram-v1 / gram-v2 otherwise).
Without AIEV_MODEL everything runs on the stub, which only tests this script.
"""
import contextlib
import csv
import datetime
import io
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import _root  # noqa: E402,F401

import assemble as A  # noqa: E402
import graph as G  # noqa: E402
import lifecycle as L  # noqa: E402
import llm  # noqa: E402
import metrics as M  # noqa: E402
import ollama_model  # noqa: E402
import precedence as P  # noqa: E402
import rerank as R  # noqa: E402
import vectors as V  # noqa: E402
from store import HANDBOOK  # noqa: E402

REAL = ollama_model.selected()
MODEL = llm.name()
TAG = (REAL or "stub").replace(":latest", "")
DATE = datetime.date.today().isoformat()
OUT = Path(os.environ.get("AIEV_RUNS_DIR", HERE))
EMBED_A = os.environ.get("AIEV_EMBED_A", "ollama:nomic-embed-text" if REAL else "gram-v1")
EMBED_B = os.environ.get("AIEV_EMBED_B", "ollama:mxbai-embed-large" if REAL else "gram-v2")

# ---- model call and token meter (Ollama's prompt_eval_count / eval_count) ----
METER = dict(calls=0, prompt=0, output=0)
_post = ollama_model._post


def _metered(body):
    data = _post(body)
    METER["calls"] += 1
    METER["prompt"] += data.get("prompt_eval_count", 0) or 0
    METER["output"] += data.get("eval_count", 0) or 0
    return data


ollama_model._post = _metered


def meter_reset():
    METER.update(calls=0, prompt=0, output=0)


def header(ch, extra=""):
    print(f"{ch} real run  model={MODEL}  seed={llm.SEED} temperature={llm.TEMPERATURE}  "
          f"date={DATE}{extra}")


# ---- Ch 10: calibrate the abstain floor on real embedder scores ----
def ch10():
    header("Ch 10", f"  embedder={EMBED_A}")
    print("dev cases: the Ch 6 golden set over Ch 6 DOCS and the Ch 8 golden set over Ch 8")
    print("CHUNKS, one source ('docs'). score = top-1 cosine; right = top-1 is the labelled id.")
    print("Alternate cases go to dev and held-out. These are retrieval checks, graded by code.")
    rows = []
    for corpus, golden in ((V.DOCS, V.GOLDEN), (R.CHUNKS, R.GOLDEN)):
        vecs = {d: V.embed(t, EMBED_A) for d, t in corpus.items()}
        for q, want in golden:
            qv = V.embed(q, EMBED_A)
            s = {d: V.dot(qv, v) for d, v in vecs.items()}
            top = max(s, key=lambda d: (s[d], d))
            rows.append((round(s[top], 4), int(top == want), q, top, want))
    dev, held = rows[0::2], rows[1::2]
    for name, part in (("dev", dev), ("held", held)):
        for sc, ok, q, top, want in part:
            print(f"  {name:4} score={sc:.4f} right={ok} top={top} want={want}  {q}")
    P.SCORES = {"docs": {"dev": [(s, ok) for s, ok, *_ in dev],
                         "held": [(s, ok) for s, ok, *_ in held]}}
    f = P.calibrate("docs")
    d, h = P.outcome(P.SCORES["docs"]["dev"], f), P.outcome(P.SCORES["docs"]["held"], f)
    print(f"docs floor={f:.2f}  dev right={d[0]}/{d[1]}  held-out right={h[0]}/{h[1]}")
    print(f"floors searched: {P.FLOORS[0]:.2f}..{P.FLOORS[-1]:.2f} step 0.05")


# ---- Ch 11: raw replies per k, with and without a distractor ----
DISTRACTOR = "store-window"           # unrelated to all six held-out questions


def ch11(sheet):
    header("Ch 11")
    print("Six held-out questions, pack_for(question, k), with and without one unrelated")
    print(f"passage ({DISTRACTOR}). Replies are graded BY HAND in the grading sheet;")
    print("coverage and the citation check below are code checks, not accuracy.")
    for dist in (False, True):
        for k in (2, 3, 5, 10):
            for n, (q, need) in enumerate(A.HELD_OUT, 1):
                pack = A.pack_for(q, k)
                if dist:
                    pack = pack + [(f"S{len(pack) + 1}",
                                    dict(id=DISTRACTOR, source="manual", score=0.0,
                                         text=R.CHUNKS[DISTRACTOR]))]
                action, reply = A.answer(q, pack)
                ok, cited, unknown = A.validate_citations(reply, pack)
                ids = [p["id"] for _, p in pack]
                covered = need <= set(ids)
                print(f"  k={k:<2} distractor={'yes' if dist else 'no '} q{n} covered={covered} "
                      f"citations_in_pack={ok} -> {action}")
                print(f"     reply: {reply}")
                sheet.append(dict(
                    chapter="11", case=f"q{n}", k=k, distractor="yes" if dist else "no",
                    question=q,
                    needed_passages=" | ".join(f"{i}: {R.CHUNKS[i]}" for i in sorted(need)),
                    pack_ids=" ".join(ids), needed_in_pack="yes" if covered else "no",
                    citations_in_pack="yes" if ok else "no", reply=reply))


# ---- Ch 13: graph hops vs plain RAG ----
REFERENCE = {"NW charger": "covered", "NW-500 ear tips": "excluded", "NW-500 cable": "unknown"}
GSYS = ('You answer whether a part is covered by the "W2 bundle warranty", only from the '
        'evidence. Reply as JSON: {"verdict": "covered" | "excluded" | "unknown", '
        '"reply": "..."}. If the evidence does not say, the verdict is "unknown".')


def _stub13(user):
    return {"verdict": "unknown", "reply": "The evidence does not say."}


def ch13():
    header("Ch 13", f"  plain-RAG embedder={EMBED_A} k=5")
    print("Reference verdicts are the graph fixture's (covered / excluded / unknown);")
    print("verdicts are compared by code. Tokens are Ollama's prompt_eval_count + eval_count.")
    vecs = {d: V.embed(t, EMBED_A) for d, t in V.DOCS.items()}
    g_ok = r_ok = 0
    meter_reset()
    for part, ref in REFERENCE.items():
        verdict, hops = G.coverage(part)
        g_ok += verdict == ref
        path = " ; ".join(f"{a} -{rel}-> {b} [{src}]" for a, rel, b, src in hops)
        print(f"  graph  {part}: verdict={verdict} steps={len(hops)} path={path or 'none'}")
    print(f"graph  correct={g_ok}/{len(REFERENCE)} model_calls=0 tokens=0")
    for part, ref in REFERENCE.items():
        q = f"Is the {part} covered by the bundle warranty?"
        qv = V.embed(q, EMBED_A)
        top = sorted(vecs, key=lambda d: (-V.dot(qv, vecs[d]), d))[:5]
        ev = "\n".join(f"[{d}] {V.DOCS[d]}" for d in top)
        reply, raw = llm.ask_json(GSYS, f"Question: {q}\n\nEvidence:\n{ev}", _stub13)
        v = (reply or {}).get("verdict")
        r_ok += v == ref
        print(f"  plain  {part}: retrieved={top} verdict={v} reference={ref}")
        print(f"     raw: {raw}")
    print(f"plain  correct={r_ok}/{len(REFERENCE)} model_calls={METER['calls']} "
          f"tokens={METER['prompt'] + METER['output']} "
          f"(prompt={METER['prompt']} output={METER['output']})")


# ---- Ch 14: real embedder migration ----
def ch14():
    header("Ch 14", f"  v1={EMBED_A} v2={EMBED_B}")
    src = L.sources()
    live = L.build(src, "INDEX v1", EMBED_A)
    cand = L.build(src, "INDEX v2", EMBED_B)
    for ix in (live, cand):
        hit, n = L.recall(ix)
        print(f"  {ix.name} model={ix.model} held-out recall@1={hit}/{n} check={L.check(src, ix)}")
    new, why = L.switch(live, cand, src)
    print(f"switch {why} -> live={new.name}")


# ---- Ch 15: llama3.2 as judge ----
JSYS = ("Two replies answer the same customer question. Pick the one that is better "
        'supported and more correct. Reply as JSON: {"better": "first" | "second"}')
UNPARSED = []


def _stub15(user):
    first = user.split("First reply: ", 1)[1].split("\nSecond reply: ", 1)[0]
    second = user.split("\nSecond reply: ", 1)[1]
    return {"better": M.stub_judge("", first, second)}


_cache = {}


def judge(q, first, second):
    key = (q, first, second)
    if key not in _cache:
        reply, raw = llm.ask_json(JSYS, f"Question: {q}\nFirst reply: {first}\nSecond reply: {second}",
                                  _stub15, max_output_tokens=40)
        v = (reply or {}).get("better")
        if v not in ("first", "second"):
            UNPARSED.append((q, raw))
            v = "first"                     # counted below; a parse failure is never hidden
        _cache[key] = v
    return _cache[key]


def ch15():
    header("Ch 15")
    agree, n = M.agreement(judge)
    fl = M.flips(judge)
    tr = M.trusted(judge)
    for (q, *_ , h), v, s in zip(M.PAIRS, M.judge_pairs(judge), M.judge_pairs(judge, swap=True)):
        print(f"  {q:18} human={h} judge={v} swapped={s}{'  FLIP' if v != s else ''}")
    print(f"judge agreement={agree}/{n} flips={fl}/{n} trusted={tr} labelled_set={n}")
    print(f"unparsed replies (counted as 'first'): {len(UNPARSED)}")
    for q, raw in UNPARSED:
        print(f"  unparsed {q}: {raw[:120]!r}")


# ---- Ch 16: raw replies for the BENCH cases that have fixture evidence ----
def _p(i, text, source="policy", score=0.8):
    return dict(id=i, source=source, score=score, text=text)


def _clauses(ids):
    kept, _, esc = P.precedence(ids)
    return [_p(i, P.CLAUSES[i]["text"], P.CLAUSES[i]["source"]) for i in kept], esc


def _edges(part):
    return [_p(f"edge:{a}>{b}", f"{a} {rel} {b} (source: {s}).", "manual")
            for a, rel, b, s in G.EDGES]


def bench_cases():
    """(case, question, passages, needed ids). Questions are written for this script;
    every passage is an existing fixture. Cases with no fixture evidence are skipped."""
    eu = [_p("S5", HANDBOOK["S5"]), _p("S3", HANDBOOK["S3"], score=0.6)]
    old_new, _ = _clauses(["R1@2026-06-01", "R1@2026-09-15"])
    tick, _ = _clauses(["R1@2026-09-15", "ticket-8812"])
    q_life = "Does the NW-500 have a lifetime warranty?"
    q_fs = "Can I get a refund on the clearance jacket?"
    return [
        ("eu-withdrawal", "How long do I have to withdraw from an online order in the EU?",
         eu, {"S5"}),
        ("old-vs-new-window", "How many days do I have to return an item in India?",
         old_new, {"R1@2026-09-15"}),
        ("refund-vs-ticket", "An agent told me returns are 7 days only now. Is that right?",
         tick, {"R1@2026-09-15"}),
        ("bundle-charger", "Is the NW charger covered by the bundle warranty?",
         _edges("NW charger"), {"edge:NW-500 charger>NW-500 Travel Bundle",
                                "edge:NW-500 Travel Bundle>W2 bundle warranty"}),
        ("final-sale-refund", q_fs,
         [p for _, p in A.pack_for(q_fs, 5)], {"jacket-sale", "ret-final"}),
        ("lifetime-warranty", q_life, [p for _, p in A.pack_for(q_life, 5)], set()),
        ("unknown-part", "Is the NW-500 cable covered by the bundle warranty?",
         _edges("NW-500 cable"), set()),
    ]


def ch16(sheet):
    header("Ch 16")
    print("Each case: fixture passages -> assemble -> answer -> citation check. Graded BY HAND")
    print("(correct / wrong / abstained) in the grading sheet; gate() is not run here.")
    done = set()
    for case, q, passages, need in bench_cases():
        pack, _ = A.assemble(passages, budget=400)
        action, reply = A.answer(q, pack)
        ok, _, _ = A.validate_citations(reply, pack)
        done.add(case)
        cat, answerable, critical = next((c, a, k) for i, c, a, k in G_BENCH if i == case)
        print(f"  {case}: answerable={answerable} critical={critical} citations_in_pack={ok} -> {action}")
        print(f"     reply: {reply}")
        texts = {p['id']: p['text'] for _, p in pack}
        sheet.append(dict(
            chapter="16", case=case, k="", distractor="", question=q,
            needed_passages=(" | ".join(f"{i}: {texts.get(i, '(not in pack)')}" for i in sorted(need))
                             or "none: expected to abstain"),
            pack_ids=" ".join(texts), needed_in_pack="yes" if need <= set(texts) else "no",
            citations_in_pack="yes" if ok else "no", reply=reply))
    skipped = [c for c, *_ in G_BENCH if c not in done]
    print(f"run={len(done)}/{len(G_BENCH)}; no fixture question/evidence, not run: {', '.join(skipped)}")


import gate as _gate  # noqa: E402
G_BENCH = _gate.BENCH

CHAPTERS = (("ch10", ch10), ("ch11", ch11), ("ch13", ch13), ("ch14", ch14),
            ("ch15", ch15), ("ch16", ch16))
FIELDS = ["chapter", "case", "k", "distractor", "question", "needed_passages", "pack_ids",
          "needed_in_pack", "citations_in_pack", "reply", "grade", "grader", "notes"]


def main():
    # Optional chapter filter: python3 vol3/runs/real_runs.py ch16  (default: all six).
    only = set(sys.argv[1:])
    unknown = only - {c for c, _ in CHAPTERS}
    if unknown:
        sys.exit(f"unknown chapter(s): {', '.join(sorted(unknown))}")
    sheet = []
    for ch, fn in CHAPTERS:
        if only and ch not in only:
            continue
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            fn(sheet) if ch in ("ch11", "ch16") else fn()
        path = OUT / f"{DATE}-{TAG}-{ch}-real.txt"
        path.write_text(buf.getvalue())
        print(f"wrote {path}", flush=True)
    suffix = "-" + "-".join(sorted(only)) if only else ""
    path = OUT / f"{DATE}-{TAG}-grading-sheet{suffix}.csv"
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        for row in sheet:
            w.writerow({**row, "grade": "", "grader": "", "notes": ""})
    print(f"wrote {path} ({len(sheet)} rows; grade: correct / wrong / abstained, by hand)")


if __name__ == "__main__":
    main()

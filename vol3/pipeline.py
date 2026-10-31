"""Capstone: one connected request path over the Vol 3 fixtures.

capstone.py tours each stage on its own fixture. This module joins them: every
stage below reads what the stage before it produced, for one ticket.

  index time   Ch 2 ingest the manuals (stable ids, provenance)
               Ch 3 parse the warranty card (table rows kept, OCR-flagged text held back)
               Ch 4 cut the returns handbook at its headings, tags kept
               + the Ch 5 help-centre rows (two tenants, internal notes) and the
                 Ch 10 clause history (old, current and future versions, one ticket)
               Ch 14 build the index version and check it before it serves
               Ch 6 the clustered vector index, under its embedding contract
  request      Ch 9 rewrite the message into parts and check meaning was kept
               Ch 1 name what each part needs; the router picks the path
               Ch 12 counted record questions: QuerySpec -> scoped, parameterized SQL
               Ch 13 coverage questions: bounded graph walk (unknown escalates)
               Ch 6 + Ch 7 document questions: vector lane, BM25 lane, exact-id lane, RRF
               Ch 5 access filter at search and again at cite
               Ch 4 applicability gate on tagged clauses
               Ch 10 precedence over clause versions (conflict escalates)
               Ch 8 rerank the survivors
               Ch 11 one evidence pack: dedupe, order, budget; citations checked
  after        Ch 15 per-ticket retrieval, context and citation metrics
               Ch 16 the gate over a small labelled ticket set, two configurations

What is still scripted: the answer is a DEMONSTRATION reader (it quotes the top
passage for each part, it is not a model), the Ch 9 rewriter, Ch 1 classifier and
Ch 12 spec writer are the chapters' stubs unless AIEV_MODEL is set, the reranker is
Ch 8's word-overlap stub, and every label in TICKETS was written by hand for this
fixture. Grading is by code against those labels, not by people.

The Budget counts work, never time: embeddings, vectors scored, centroid
comparisons, BM25 documents scored, reranker pairs, SQL queries, graph edges read,
model calls and pack tokens (Vol 1's PLACEHOLDER counter). The limits in LIMITS are
PLACEHOLDERS for this fixture, not recommendations. Run from the repo root:
    python3 vol3/pipeline.py
"""
import json
import re
from dataclasses import dataclass, field

import _root  # noqa: F401

import access as A
import assemble as AS
import chunking as C
import gate as GT
import graph as GR
import hybrid as H
import ingest as I
import layout as LY
import lifecycle as LC
import llm
import metrics as M
import precedence as P
import query as Q
import rerank as R
import sources as S
import structured as ST
import vectors as V

AS.AUTHORITY.setdefault("orders", 3)     # a scoped record decides (Ch 1 contract)
AS.AUTHORITY.setdefault("graph", 3)      # an edge chain that ends at a policy clause
MODEL = "gram-v1"                        # the Ch 6 winner on its golden set
SEEDS = ("handbook-returns@2026-09-15:R1", "handbook-returns@2026-09-15:R2",
         "man-nw500@2026-07-01:p2.b1", "warranty-nw500@2026-08-01:p2.e2")
LIMITS = dict(reranker_pairs=60, pack_tokens=120, model_calls=8, sql_queries=2,
              graph_edges_max=24)            # PLACEHOLDERS: per-ticket caps for this fixture
K_LANE, K_FUSED, N_RERANK = 8, 10, 2      # PLACEHOLDERS for this fixture
COUNT_RE = re.compile(r"\bhow many (?:refunds|orders)\b.*\b(?:i|my)\b|\bwhich of my orders\b", re.I)
MAN_PRODUCT = {"man-nw500": "nw-500", "man-dl1": "lamp", "man-tf20": "fan"}


@dataclass
class Budget:
    """Counts only. Nothing here is a time or a price; convert with your own measurements."""
    limits: dict = field(default_factory=lambda: dict(LIMITS))
    counts: dict = field(default_factory=dict)

    def add(self, what, n=1):
        self.counts[what] = self.counts.get(what, 0) + n

    def over(self):
        return [k for k, cap in self.limits.items() if self.counts.get(k, 0) > cap]


# ---------- index time ----------

def corpus():
    """One corpus from the chapters' fixtures. Each row keeps where it came from."""
    rows = {}
    store = I.Store()
    I.ingest(sorted(I.MANUALS.glob("*.txt")), store, echo=False)            # Ch 2
    for cid, c in store.chunks.items():
        rows[cid] = dict(text=c["text"], kind="manual", tenant="a", audience="customer",
                         product=MAN_PRODUCT.get(c["source"]), stage="ch02")
    held = 0
    for c in LY.run(echo=False)["chunks"]:                                   # Ch 3
        if c["flagged"]:
            held += 1                    # low OCR confidence: a person reads it first
            continue
        if c["kind"] != "heading":
            rows[c["id"]] = dict(text=c["text"], kind="manual", tenant="a",
                                 audience="customer", product="nw-500", stage="ch03")
    meta, body = C.read()                                                    # Ch 4
    for c in C.section_chunks(meta, body):
        rows[c["id"]] = dict(text=c["title"] + ". " + c["text"], kind="policy", tenant="a",
                             audience="customer", tags=c["tags"], stage="ch04")
    for cid, _, tenant, aud, text in A.CHUNKS:                                # Ch 5
        rows[cid] = dict(text=text, kind="faq", tenant=tenant, audience=aud, stage="ch05")
    for cid, c in P.CLAUSES.items():                                          # Ch 10
        rows[cid] = dict(text=c["text"], kind=c["source"], tenant="a", audience="customer",
                         stage="ch10")
    return rows, dict(chunks=len(rows), ocr_held=held)


class Pipeline:
    def __init__(self, use_access=True, use_applies=True, use_precedence=True, lane=True,
                 limits=None):
        self.limits = dict(limits or LIMITS)
        self.cfg = dict(access=use_access, applies=use_applies, precedence=use_precedence,
                        lane=lane)
        self.rows, self.built = corpus()
        src = {i: dict(text=r["text"], audience=r["audience"], version=1)
               for i, r in self.rows.items()}
        self.version = LC.build(src, "v3-capstone", MODEL)                    # Ch 14
        self.check = LC.check(src, self.version)
        if any(self.check[k] for k in ("orphans", "stale", "missing", "mixed")):
            raise RuntimeError(f"index refused: {self.check}")
        texts = {i: r["text"] for i, r in self.rows.items()}
        self.vectors = V.ClusteredIndex(texts, MODEL, SEEDS)                  # Ch 6
        self.words = H.BM25(texts)                                            # Ch 7
        self.ids = {i: set(H.normalize_id(t)) for i, t in texts.items()}
        self.access = A.Index([(i, i, r["tenant"], r["audience"], r["text"])  # Ch 5
                               for i, r in self.rows.items()])
        self.built["embeddings"] = 2 * len(texts)   # the version build and the clustered index

    # ---------- request time ----------

    def route(self, part, b):
        """Ch 1 names the needs; this router adds two paths the chapters built later."""
        b.add("model_calls")
        need, _ = S.classify(part)
        if COUNT_RE.search(part):
            return "records", need
        if need and "warranty" in need and "covered" in part.lower() and self.entity(part):
            return "graph", need
        if not need:                     # Ch 9's router is the fallback
            return ("documents", need) if Q.route(part) != "ask" else ("ask", need)
        return "documents", need

    @staticmethod
    def entity(part):
        low = part.lower()
        hits = [a for a in GR.ALIASES if re.search(rf"\b{re.escape(a)}\b", low)]
        return GR.resolve(max(hits, key=len)) if hits else None

    def records(self, part, session, b):                                      # Ch 12
        b.add("model_calls")
        b.add("sql_queries")
        res, why = ST.try_ask(part, session)
        if res is None:
            return dict(escalate=f"query refused: {why}", evidence=[])
        spec, sql, params, rows = res
        year = f" in {spec['year']}" if spec.get("year") else ""
        value = rows[0][0] if len(rows) == 1 and len(rows[0]) == 1 else rows
        text = f"Your {spec['metric'].replace('_', ' ')}{year} (your own records only): {value}."
        return dict(evidence=[dict(id=f"sql:{spec['metric']}", source="orders", score=1.0,
                                   text=text)], sql=sql)

    def graph(self, part, b):                                                 # Ch 13
        node = self.entity(part)
        b.add("graph_edges_max", len(GR.EDGES) * GR.MAX_HOPS)   # upper bound: a hop scans the edge list
        verdict, hops = GR.coverage(node)
        if verdict == "unknown":
            return dict(escalate=f"{node}: no edge to the warranty (unknown, not no)", evidence=[])
        chain = "; ".join(f"{a} {r} {c} ({src})" for a, r, c, src in hops)
        return dict(evidence=[dict(id=f"graph:{node}", source="graph", score=1.0,
                                   text=f"{node} is {verdict}: {chain}.")], verdict=verdict)

    def documents(self, part, session, b):
        cfg = self.cfg
        b.add("query_embeddings")
        meaning, scored = self.vectors.query(part, V.contract(MODEL), K_LANE, probe=2)   # Ch 6
        b.add("vectors_scored", scored)
        b.add("centroid_comparisons", self.vectors.routing_cost())
        ws = self.words.scores(part)                                                     # Ch 7
        b.add("bm25_docs_scored", len(ws))
        words = [d for d in H.ranked(ws) if ws[d] > 0][:K_LANE]
        fused = H.rrf([meaning, words])
        want = set(H.normalize_id(part))
        if cfg["lane"] and want:
            fused = [d for d in fused if want <= self.ids[d]] + \
                    [d for d in fused if not want <= self.ids[d]]
        fused = fused[:K_FUSED]
        trail = {"fused": list(fused)}
        if cfg["access"]:                                                                # Ch 5
            trail["access_dropped"] = [d for d in fused if not self.access.may_see(session, d)]
            fused = [d for d in fused if self.access.may_see(session, d)]
        if cfg["applies"]:                                                               # Ch 4
            product = next(iter(sorted(Q.facts(part)["entities"])), "unknown")
            keep, out = [], []
            for d in fused:
                tags = self.rows[d].get("tags")
                ok = tags is None or C.applies(tags, product, session.region)[0]
                (keep if ok else out).append(d)
            fused, trail["not_applicable"] = keep, out
        b.add("reranker_pairs", len(fused))                                               # Ch 8
        score = {d: R.stub_score(part, self.rows[d]["text"]) for d in fused}
        ranked = [d for d in sorted(fused, key=lambda d: (-score[d], fused.index(d))) if score[d] > 0]
        escalate, gone = None, set()
        top = ranked[:N_RERANK]
        while cfg["precedence"]:                                                          # Ch 10
            # every clause family that reaches the pack is judged with all its
            # retrieved versions, not only the ones that ranked high
            fams = {P.CLAUSES[d]["family"] for d in top if d in P.CLAUSES}
            group = [d for d in fused if d in P.CLAUSES and P.CLAUSES[d]["family"] in fams]
            if not group:
                break
            _, dropped, esc = P.precedence(group, session.region)
            escalate = escalate or ("sources disagree at the same authority and date" if esc else None)
            new_gone = gone | {d for d, _ in dropped}
            new_top = [d for d in ranked if d not in new_gone][:N_RERANK]
            if new_top == top and new_gone == gone:
                break
            gone, top = new_gone, new_top
        if cfg["precedence"]:
            trail["precedence_dropped"] = sorted(gone)
        trail["reranked"] = top
        if not top and not escalate:
            escalate = "no passage left after the filters"
        ev = [dict(id=d, source=self.rows[d]["kind"], score=1 - n / 100, text=self.rows[d]["text"])
              for n, d in enumerate(top)]
        return dict(evidence=ev, escalate=escalate, trail=trail)

    def answer(self, message, session, history=None):
        b = Budget(dict(self.limits))
        b.add("model_calls")                                                              # Ch 9
        steps = Q.understand(message, history or {})
        kinds = dict((k, v) for k, v in steps if k != "route")
        if "clarify" in kinds:
            return dict(action="clarify", reply=kinds["clarify"], parts=[], budget=b, steps=steps)
        parts = kinds.get("rewrite") or [kinds["pass"]]
        done, evidence = [], []
        for part in parts:
            path, need = self.route(part, b)                                              # Ch 1
            if path == "records":
                r = self.records(part, session, b)
            elif path == "graph":
                r = self.graph(part, b)
            elif path == "documents":
                r = self.documents(part, session, b)
            else:
                r = dict(escalate="no source answers this part", evidence=[])
            r.update(part=part, path=path, need=need)
            done.append(r)
            evidence += [e for e in r["evidence"] if e["id"] not in {x["id"] for x in evidence}]
        pack, stats = AS.assemble(evidence, budget=self.limits["pack_tokens"])                 # Ch 11
        b.add("pack_tokens", stats["tokens"])
        label = {p["id"]: lab for lab, p in pack}
        b.add("model_calls")
        reply, _ = llm.ask_json(AS.SYSTEM, _payload(done, pack), _stub_reply)
        text = (reply or {}).get("reply", "")
        ok, cited, unknown = AS.validate_citations(text, pack)
        cited_ids = [p["id"] for lab, p in pack if lab in cited]
        docs = [i for i in cited_ids if i in self.rows]
        cite_ok = self.access.cite_ok(session, docs) if self.cfg["access"] else True       # Ch 5
        why = [f"part {n}: {r['escalate']}" for n, r in enumerate(done, 1) if r.get("escalate")]
        if not ok:
            why.append(f"citations not in pack: {unknown or 'none cited'}")
        if not cite_ok:
            why.append("a cited passage is not visible to this session")
        if stats["first_over"]:
            why.append(f"pack budget: {stats['first_over']} did not fit")
        over = b.over()
        if over:
            why.append(f"over budget: {', '.join(over)}")
        return dict(action="escalate" if why else "send", reply=text, why=why, parts=done,
                    pack=pack, labels=label, stats=stats, cited=cited_ids, budget=b, steps=steps)


def _payload(done, pack):
    lines = [f"Part {n}: {r['part']}" for n, r in enumerate(done, 1)]
    want = {str(n): [e["id"] for e in r["evidence"]] for n, r in enumerate(done, 1)}
    return "\n".join(lines) + "\n\n" + AS.render(pack) + "\n\nTOP " + json.dumps(want)


def _stub_reply(payload):
    """DEMONSTRATION reader, not a model: for each part, quote the first pack passage
    retrieved for it, with its label. Parts with no passage in the pack are skipped."""
    want = json.loads(payload.rsplit("TOP ", 1)[1])
    rows = re.findall(r"^\[(S\d+)\] \((.*?)\) (.*)$", payload, re.M)
    by_id = {i: lab for lab, i, _ in rows}
    texts = {lab: t for lab, _, t in rows}
    out = []
    for n in sorted(want, key=int):
        lab = next((by_id[i] for i in want[n] if i in by_id), None)
        if lab:
            out.append(f"{texts[lab]} [{lab}]")
    return {"reply": " ".join(out)}


# ---------- after: metrics and the gate over labelled tickets ----------

ASHA = A.Session("a", "asha", "customer", "IN")
ASHA_EU = A.Session("a", "asha", "customer", "EU")

# (case id, category, answerable, critical, message, session, expected action,
#  groups the pack must cover (any one id of each group), ids never to be packed or cited).
# Labels written by hand for this fixture.
R1_NOW = {"handbook-returns@2026-09-15:R1", "R1@2026-09-15"}
TICKETS = [
    ("mug-photo", "decisions", True, False,
     "My mug arrived broken, do I need to send a photo for a refund?", ASHA, "send",
     [{"handbook-returns@2026-09-15:R2", "a-ret.2"}], set()),
    ("return-window", "conflicts", True, False,
     "How many days do I have to return unused items?", ASHA, "send", [R1_NOW], set()),
    ("agent-7-days", "conflicts", True, True,
     "Are returns 7 days only now?", ASHA, "send", [R1_NOW],
     {"ticket-8812", "R1@2026-11-01", "R1@2026-06-01"}),
    ("refund-count", "records", True, False,
     "How many refunds did I get in 2026?", ASHA, "send", [{"sql:refund_count"}], set()),
    ("pair-nw500", "how-to", True, False,
     "How do I pair my NW-500 headphones?", ASHA, "send",
     [{"man-nw500@2026-07-01:p2.b1"}], set()),
    ("eu-withdrawal", "tables", True, True,
     "Can I withdraw from my online purchase in the EU?", ASHA_EU, "send",
     [{"handbook-returns@2026-09-15:S5", "R1-EU@2026-01-01"}], set()),
    ("vip-photo", "permissions", True, True,
     "Do damaged refunds need a photo for VIP accounts?", ASHA, "send",
     [{"handbook-returns@2026-09-15:R2", "a-ret.2"}], {"b-note.1", "a-note.1", "b-ret.1"}),
    ("charger-cover", "multi-hop", True, False,
     "Is my NW-500 charger covered by the bundle warranty?", ASHA, "send",
     [{"graph:NW-500 charger"}], set()),
    ("battery-cycles", "conflicts", False, True,
     "When should I replace the NW-500 battery?", ASHA, "escalate", [], set()),
    ("cable-cover", "abstain", False, True,
     "Is my NW-500 cable covered by the bundle warranty?", ASHA, "escalate", [], set()),
]
BENCH = [(c, cat, ans, crit) for c, cat, ans, crit, *_ in TICKETS]


def grade(p, case):
    """(correct, abstained) for one ticket, from the pipeline's own output."""
    _, _, _, _, msg, session, expect, must, never = case
    out = p.answer(msg, session)
    in_pack = {x["id"] for _, x in out.get("pack", [])}
    correct = (out["action"] == expect and all(g & in_pack for g in must)
               and not (never & (in_pack | set(out.get("cited", [])))))
    return (correct, out["action"] != "send"), out


def results(p):
    return {case[0]: grade(p, case)[0] for case in TICKETS}


def ticket_metrics(out, case):
    """Ch 15 metrics for one ticket, against the hand labels: did the fused list and
    the pack cover each required group, and were the citations inside the pack."""
    must = case[7]
    fused = {d for r in out["parts"] for d in r.get("trail", {}).get("fused", [])}
    pack = {x["id"] for _, x in out.get("pack", [])}
    groups = len(must)
    return dict(fused_cover=(sum(bool(g & fused) for g in must), groups),
                pack_cover=(sum(bool(g & pack) for g in must), groups),
                cite_acc=M.citation_accuracy(out.get("cited", []), pack))


CONFIGS = {"no_precedence": dict(use_precedence=False), "full": {},
           "no_access_filter": dict(use_access=False)}


def run_gate(base="no_precedence", new="full"):
    rb, rn = results(Pipeline(**CONFIGS[base])), results(Pipeline(**CONFIGS[new]))
    return GT.gate_results(rb, rn, BENCH)


DEMO = ("My mug arrived broken, do I need to send a photo for a refund? "
        "How many refunds did I get in 2026? Is my NW-500 charger covered by the bundle warranty?")


def main():
    p = Pipeline()
    print(f"index   chunks={p.built['chunks']} ocr_held={p.built['ocr_held']} "
          f"check={p.check}")
    out = p.answer(DEMO, ASHA)
    if out["action"] == "clarify":      # the Ch 9 step asked a question instead of splitting
        print(f"action  clarify: {out['reply']}")
        print("budget  " + " ".join(f"{k}={v}" for k, v in sorted(out["budget"].counts.items())))
    for n, r in enumerate(out["parts"], 1):
        ids = [e["id"] for e in r["evidence"]]
        print(f"part {n}  {r['path']:<9} {r['part']}")
        t = r.get("trail")
        if t:
            print(f"        fused={len(t['fused'])} access_dropped={t.get('access_dropped')} "
                  f"not_applicable={t.get('not_applicable')}")
            print(f"        precedence_dropped={t.get('precedence_dropped')} reranked={t['reranked']}")
        print(f"        evidence={ids}" + (f" escalate={r['escalate']}" if r.get("escalate") else ""))
    if out["action"] != "clarify":
        s = out["stats"]
        print(f"pack    in={s['n_in']} dupes={s['dupes']} kept={s['kept']} tokens={s['tokens']}/{s['budget']}")
        print(f"reply   {out['reply']}")
        print(f"action  {out['action']} cited={out['cited']} {out['why'] or ''}")
        print("budget  " + " ".join(f"{k}={v}" for k, v in sorted(out["budget"].counts.items())))
    p = Pipeline()
    for case in TICKETS:
        (ok, _), o = grade(p, case)
        m = ticket_metrics(o, case)
        print(f"ticket  {case[0]:<15} {o['action']:<9} correct={ok!s:<5} "
              f"pack_cover={m['pack_cover'][0]}/{m['pack_cover'][1]} "
              f"model_calls={o['budget'].counts.get('model_calls', 0)} "
              f"reranker_pairs={o['budget'].counts.get('reranker_pairs', 0)}")
    for base, new in (("full", "no_precedence"), ("full", "no_access_filter")):
        g = run_gate(base, new)
        print(f"gate    {base} -> {new}: answered={g.get('answered')}/{g.get('answerable')} "
              f"critical={g['critical'] or 'none'} -> {g['label']}")


if __name__ == "__main__":
    main()

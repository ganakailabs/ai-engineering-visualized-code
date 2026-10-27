"""RAG metrics, a stage scorecard, ablation and a checked judge (Vol 3 Ch 15).

Every metric code can compute is here, each in the chapter's own definition.
The pipeline below is scripted fixture data (a demonstration): its stage
outputs are fixed so that every number in the chapter can be recomputed.
"""
import math

# ---------- retrieval (top k) ----------

def hit_rate(cases, k):
    """Share of cases with at least one relevant id in the top k."""
    return sum(bool(set(r[:k]) & rel) for r, rel in cases) / len(cases)


def recall_at_k(ranked, rel, k):
    """Share of the relevant ids found in the top k (0 when none exist)."""
    return len(set(ranked[:k]) & rel) / len(rel) if rel else 0.0


def precision_at_k(ranked, rel, k):
    """Share of the top k that are relevant."""
    return len(set(ranked[:k]) & rel) / k


def rr(ranked, rel):
    """One over the rank of the first relevant id; 0 when none is found."""
    for i, d in enumerate(ranked, 1):
        if d in rel:
            return 1 / i
    return 0.0


def mrr(cases):
    return sum(rr(r, rel) for r, rel in cases) / len(cases)


def ndcg_at_k(ranked, rel, k):
    """Binary-gain DCG of the top k divided by the ideal order's DCG."""
    dcg = sum(1 / math.log2(i + 1) for i, d in enumerate(ranked[:k], 1) if d in rel)
    ideal = sum(1 / math.log2(i + 1) for i in range(1, min(len(rel), k) + 1))
    return dcg / ideal if ideal else 0.0

# ---------- context (the evidence pack) ----------

def context_precision(pack, rel):
    return len(set(pack) & rel) / len(pack) if pack else 0.0


def context_recall(pack, needed):
    """Share of the facts the reference needs that the pack supports."""
    return len(set(pack) & needed) / len(needed) if needed else 1.0

# ---------- citations ----------

def citation_accuracy(cited, supported):
    """Share of citations whose passage supports its sentence."""
    return len([c for c in cited if c in supported]) / len(cited) if cited else 0.0


def citation_coverage(claims_cited, claims):
    return claims_cited / claims if claims else 1.0

# ---------- abstain ----------

def abstain_rates(rows):
    """rows: (answerable, abstained). Returns (correct, unanswerable, false, answerable)."""
    un = [a for ok, a in rows if not ok]
    an = [a for ok, a in rows if ok]
    return sum(un), len(un), sum(an), len(an)


def p95(xs):
    s = sorted(xs)
    return s[max(0, math.ceil(0.95 * len(s)) - 1)]

# ---------- the scripted pipeline (fixture) ----------

RERANK = {"P1": .9, "P2": .4, "P3": .8, "P4": .7, "P5": .3, "P6": .85,
          "P7": .2, "P8": .75, "P9": .6, "P10": .5, "P11": .65, "P12": .1}
CASES = [  # question, relevant ids, first-stage ranking, reference decision
    ("q1 refund window for unused NW-500", {"P1"}, ["P1", "P9", "P2", "P5", "P7", "P10"], "refund"),
    ("q2 NW-550 battery warranty in IN", {"P3"}, ["P9", "P3", "P2", "P10", "P5", "P7"], "cover"),
    ("q3 final-sale jacket return", {"P4", "P2"}, ["P4", "P11", "P2", "P6", "P5", "P7"], "deny"),
    ("q4 EU withdrawal period", {"P5"}, ["P5", "P6", "P8", "P9", "P2", "P7"], "refund"),
    ("q5 bundle charger cover", {"P8", "P10"}, ["P8", "P10", "P6", "P1", "P2", "P7"], "cover"),
    ("q6 opened earbuds return", {"P2"}, ["P9", "P11", "P10", "P7", "P5", "P12"], "deny"),
    ("q7 gift card refund", set(), ["P9", "P11", "P2", "P7", "P5", "P12"], "abstain"),
    ("q8 lifetime warranty", set(), ["P6", "P3", "P9", "P10", "P7", "P12"], "abstain"),
]
ANSWER_SLIPS = {"q5"}          # the answer stage gets this one wrong with the right pack
FALSE_ANSWER = {"q8"}          # answers an unanswerable case
PACK = 2
STAGES = ("retrieve", "rerank", "answer")


def run_case(case, oracle=()):
    q, rel, first, ref = case
    tag = q.split()[0]
    ids = list(first)
    if "retrieve" in oracle:    # every relevant id caught, ahead of the rest
        ids = sorted(rel) + [d for d in ids if d not in rel]
    order = (sorted(ids, key=lambda d: d not in rel) if "rerank" in oracle
             else sorted(ids, key=lambda d: -RERANK[d]))
    pack = order[:PACK] if "pack" not in oracle else (
        [d for d in order if d in rel] or order[:PACK])
    if "answer" in oracle:      # a perfect reader of this pack, not the answer key
        out = ref if (rel <= set(pack) if rel else True) else "abstain"
    elif not rel:
        out = "refund" if tag in FALSE_ANSWER else "abstain"
    elif rel <= set(pack):
        out = "wrong" if tag in ANSWER_SLIPS else ref
    elif rel & set(pack):
        out = "wrong"
    else:
        out = "abstain"
    cited = [] if out == "abstain" else pack
    return dict(q=tag, rel=rel, ranked=ids, order=order, pack=pack, out=out,
                ref=ref, cited=cited, latency=40 + 15 * len(ids) + 30 * len(pack) + 25 * len(rel))


def end_score(oracle=()):
    return sum(r["out"] == r["ref"] for r in map(lambda c: run_case(c, oracle), CASES))


def scorecard(k=5):
    rows = [run_case(c) for c in CASES]
    ans = [r for r in rows if r["rel"]]
    pairs = [(r["ranked"], r["rel"]) for r in ans]
    claims = sum(len(r["rel"]) for r in ans if r["out"] != "abstain")
    cited_claims = sum(len(set(r["cited"]) & r["rel"]) for r in ans)
    cites = [c for r in rows for c in r["cited"]]
    sup = {c for r in rows for c in r["cited"] if c in r["rel"]}
    ca, cn, fa, an = abstain_rates([(bool(r["rel"]), r["out"] == "abstain") for r in rows])
    return dict(
        hit=hit_rate(pairs, k),
        recall=sum(recall_at_k(r, rel, k) for r, rel in pairs) / len(pairs),
        precision=sum(precision_at_k(r, rel, k) for r, rel in pairs) / len(pairs),
        mrr=mrr(pairs),
        ndcg=sum(ndcg_at_k(r, rel, k) for r, rel in pairs) / len(pairs),
        ctx_p=sum(context_precision(r["pack"], r["rel"]) for r in ans) / len(ans),
        ctx_r=sum(context_recall(r["pack"], r["rel"]) for r in ans) / len(ans),
        correct=end_score(), n=len(rows),
        cite_acc=citation_accuracy(cites, sup),
        cite_cov=citation_coverage(cited_claims, claims),
        abstain=(ca, cn, fa, an),
        p95=p95([r["latency"] for r in rows]),
        cost=sum(r["latency"] for r in rows) / len(rows))


def ablation():
    base = end_score()
    return {s: end_score((s,)) - base for s in STAGES}


def limiting_stage():
    gains = ablation()
    return max(gains, key=gains.get), gains

# ---------- the judge ----------

# (question, reply A, reply B, human label of the better reply)
PAIRS = [
    ("refund window", "30 days for unused items [S1].", "Unused items can be refunded within 30 days of delivery, and here is a lot more background on our refund history [S1].", "A"),
    ("EU withdrawal", "14 days in the EU [S5].", "You may have a while.", "A"),
    ("battery warranty", "Two years in IN [P3].", "One year [P3], although the manual describes many other details about care, cleaning and storage at length.", "A"),
    ("final sale", "Final-sale items cannot be returned [P4].", "No returns on final sale [P4].", "A"),
    ("charger cover", "Covered by the bundle warranty [P8][P10].", "Covered.", "A"),
    ("opened earbuds", "Hygiene rules: opened earbuds cannot be returned [P2].", "They cannot be returned once opened, per the hygiene rule, and we recommend reading the whole policy page before contacting support again [P2].", "A"),
    ("gift card", "I can't find a rule for gift cards; escalating.", "Gift cards are refundable.", "A"),
    ("lifetime warranty", "There is no lifetime warranty; escalating to confirm.", "Yes, everything has a lifetime warranty, and this covers accidental damage, loss and theft in all regions worldwide.", "A"),
    ("exchange size", "Exchanges are allowed within 30 days [S1].", "Exchanges are allowed within 30 days for unused items with tags [S1].", "B"),
    ("stand return", "The stand follows the 30-day rule [S1].", "Stands follow the 30-day rule if unused, with the box [S1].", "B"),
]


def stub_judge(q, first, second):
    """Scripted to lean: keeps the first reply unless the second is 30% longer."""
    return "second" if len(second) > 1.3 * len(first) else "first"


def judge_pairs(judge=stub_judge, swap=False):
    out = []
    for q, a, b, _ in PAIRS:
        x, y = (b, a) if swap else (a, b)
        v = judge(q, x, y)
        out.append(("A" if (v == "first") != swap else "B"))
    return out


def agreement(judge=stub_judge):
    v = judge_pairs(judge)
    return sum(p == h for p, (*_, h) in zip(v, PAIRS)), len(PAIRS)


def flips(judge=stub_judge):
    return sum(a != b for a, b in zip(judge_pairs(judge), judge_pairs(judge, swap=True)))


def trusted(judge=stub_judge, bar=0.9):
    """Use a judge only if it agrees with human labels at least `bar` of the
    time and no verdict flips when the two replies swap places."""
    agree, n = agreement(judge)
    return agree / n >= bar and flips(judge) == 0

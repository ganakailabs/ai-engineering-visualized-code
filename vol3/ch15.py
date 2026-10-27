"""Chapter 15: Evaluating RAG: Retrieval Metrics and Faithfulness Judges.

Run from the repo root:  python3 vol3/ch15.py
Every code metric on the scripted eight-case pipeline (a demonstration), the
stage scorecard, an oracle ablation that names the limiting stage, and the
stub judge checked against human labels before it is trusted. No model is used.
"""
import _root  # noqa: F401

import metrics as M

s = M.scorecard()
print(f"retrieve hit@5={s['hit']:.2f} recall@5={s['recall']:.2f} "
      f"precision@5={s['precision']:.2f} mrr={s['mrr']:.2f} ndcg@5={s['ndcg']:.2f}")
print(f"pack     context_precision={s['ctx_p']:.2f} context_recall={s['ctx_r']:.2f}")
print(f"answer   correctness={s['correct']}/{s['n']} (code, decision vs reference)")
print(f"cite     accuracy={s['cite_acc']:.2f} coverage={s['cite_cov']:.2f}")
ca, cn, fa, an = s["abstain"]
print(f"abstain  correct={ca}/{cn} false={fa}/{an}")
print(f"cost     p95_latency={s['p95']} mean={s['cost']:.0f} (simulated units)")
stage, gains = M.limiting_stage()
for k, v in gains.items():
    print(f"ablate   {k}=oracle end_score {M.end_score()} -> {M.end_score((k,))} ({v:+d})")
print(f"ablate   retrieve+rerank=oracle end_score -> {M.end_score(('retrieve', 'rerank'))}")
print(f"limiting stage: {stage} (lowest number was precision@5, not the limiter)")
agree, n = M.agreement()
print(f"judge    agreement with human labels {agree}/{n} "
      f"-> trusted={M.trusted()}; "
      f"order swap flips {M.flips()}/{n}")

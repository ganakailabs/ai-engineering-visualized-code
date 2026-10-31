import csv
from pathlib import Path
H = Path(__file__).resolve().parent
S = list(csv.DictReader(open(H / "2026-10-28-llama3.2-strict-grading.csv")))
def esc(t): return t.replace("|", "\\|").replace("\n", " ")
def short(t, n=230): t = esc(t); return t if len(t) <= n else t[:n] + "…"
def acc(col, d, extra=lambda o: True):
    out = []
    for k in ("2", "3", "5", "10"):
        rs = [o for o in S if o["chapter"] == "11" and o["k"] == k and o["distractor"] == d]
        out.append(f"{sum(o[col]=='correct' and extra(o) for o in rs)}/6")
    return out
L = []
w = L.append
w("# Vol 3 hand grading: llama3.2 runs of Oct 27, 2026 (Ch 11 accuracy per k, Ch 16 held-out suite)\n")
w("Drafted 2026-10-28 by Grok Bot for Prateek's review. **Not final; manuscript not edited; nothing committed or pushed.**\n")
w("## Sources\n")
w("- Code clone: `/workspace/aev-code` at `3e1cd12` (\"vol3: add 2026-10-27 llama3.2 run logs for Ch 10, 11, 13-16 and the grading sheet\").")
w("- Logs graded: `vol3/runs/2026-10-27-llama3.2-ch11-real.txt`, `vol3/runs/2026-10-27-llama3.2-ch16-real.txt`, and the replies in `vol3/runs/2026-10-27-llama3.2-grading-sheet.csv` (55 rows; grade column was blank). Written by `vol3/runs/real_runs.py` on the Mac (`ollama:llama3.2`, id a80c4f17acd5, seed 7, temperature 0.0).")
w("- Expected answers: `assemble.HELD_OUT` needed-passage labels over `rerank.CHUNKS` (Ch 11); `real_runs.bench_cases()` needed ids and `gate.BENCH` answerable/critical flags (Ch 16).")
w("- Packs re-derived on the box with `assemble.pack_for()`: all 24 no-distractor packs at k=2,3,5,10 match the logged pack ids exactly.\n")
w("## Rubric\n")
w("- **strict (headline)**: correct only if the reply gives the expected answer in full and makes no claim that is false or unsupported by the pack (invented steps, recipients, conditions, or windows count as wrong). For q6 both needed passages (order number + photo; free within the 12-month warranty) must be conveyed.")
w("- **abstained**: declines or says it cannot tell, without asserting a wrong answer. Truncated replies with no answer are abstained.")
w("- **lenient (for comparison only)**: expected answer present and not contradicted; unsupported extras tolerated. Shown so you can see which verdicts hinge on strictness.")
w("- **citations**: noted separately. `action` = what `validate_citations()` did (send only if the reply has `[Sn]` labels all in the pack). `pipeline_outcome` treats an escalated reply as abstained.\n")
w("## Mark 1 and 2: Ch 11 answer accuracy per k (six held-out questions)\n")
w("**Recorded only at k = 2, 3, 5, 10.** k = 4, 6, 7, 8, 9 were never run (see Missing runs).\n")
w("| | k=2 | k=3 | k=5 | k=10 |\n|---|---|---|---|---|")
w("| coverage (code, from log) | 3/6 | 4/6 | 4/6 | 4/6 |")
w("| **accuracy, strict** | " + " | ".join(acc("strict_grade", "no")) + " |")
w("| accuracy, strict, and sent (citation check passed) | " + " | ".join(acc("strict_grade", "no", lambda o: o["action"] == "send")) + " |")
w("| accuracy, lenient (comparison) | " + " | ".join(acc("lenient_grade", "no")) + " |")
w("| **+1 unrelated passage (store-window), strict** | " + " | ".join(acc("strict_grade", "yes")) + " |")
w("| +1 unrelated passage, lenient | " + " | ".join(acc("lenient_grade", "yes")) + " |")
w("")
w("Per question (strict, no distractor): q1 return window wrong at every k (2-day courier collection and 21-day international transit reported as return windows); q4 cash on delivery wrong at every k (pay-cod never retrieved; the model answers 'No' from ret-intl); q3 jacket correct at k=2,3,5, truncated at k=10; q5 refund correct at k=5,10; q2 mug correct only at k=2 (later k add invented steps from extra passages); q6 warranty correct only at k=5.\n")
w("Note: at k=10, store-window is already in q1's natural pack, so the distractor variant for q1 contains it twice (S10 and S11).\n")
w("## Mark 3: Ch 16 held-out suite (7 of 16 BENCH cases recorded)\n")
w("| case | answerable | critical | reply content (strict) | citation check | pipeline outcome |\n|---|---|---|---|---|---|")
import sys; sys.path.insert(0, str(H.parent.parent)); import _root  # noqa
import gate
B = {c: (a, k) for c, _, a, k in gate.BENCH}
for o in S:
    if o["chapter"] == "16":
        a, k = B[o["case"]]
        w(f"| {o['case']} | {a} | {k} | {o['strict_grade']} | {o['action']} | {o['pipeline_outcome']} |")
w("")
w("- Reply content: 4/5 answerable cases correct (bundle-charger wrong); expected-abstain cases: lifetime-warranty abstained (right), unknown-part asserted a wrong exclusion. **Content right: 5/7.**")
w("- Full pipeline (escalate = abstain): answered answerable cases correctly 2/5 (refund-vs-ticket, final-sale-refund); both expected-abstain cases ended abstained (2/2), unknown-part only because its wrong reply carried no `[Sn]` labels; 1 wrong answer sent (bundle-charger). **Pipeline right: 4/7.** Critical answerable cases eu-withdrawal and old-vs-new-window were answered correctly in content but escalated (no `[Sn]` labels), so a gate on these 7 would block on 2 critical cases.")
w("- `gate()` was not run and cannot be run on 7 of 16 cases: the other 9 (in-battery-row, supplier-vs-policy, other-tenant-note, internal-only-page, revoked-page, retired-clause, stale-order-total, bundle-stand, gift-card-cash) have no fixture question/evidence in `real_runs.py`.")
w("- Harness finding: bundle-charger's needed edge (NW-500 charger PART_OF NW-500 Travel Bundle) was not in the pack. `assemble()` dropped it as a near-duplicate of the NW-500 case edge (Jaccard ≥ 0.8; stats dupes=1). The model then answered 'not covered'. This is a dedupe problem in the harness as much as a model error.\n")
w("## Borderline strict judgements (flip these if you prefer lenient)\n")
for key in [("q6","3","no"),("q2","10","no"),("q5","2","no"),("q1","5","yes"),("q3","3","yes"),("q3","5","yes")]:
    o = next(o for o in S if (o["case"], o["k"], o["distractor"]) == key)
    w(f"- **{o['case']} k={o['k']} distractor={o['distractor']}**: strict {o['strict_grade']}, lenient {o['lenient_grade']}. {esc(o['reason'])}. Reply: \"{short(o['reply'], 260)}\"")
w("")
w("## Missing runs (not invented; run on the Mac)\n")
w("1. **Ch 11, k = 4, 6, 7, 8, 9** (both marks ask for k = 2..10). New uncommitted helper in this folder, same packs/prompt/settings/distractor as `real_runs.py`; tested on the stub on the box only. From the repo root on the Mac (Ollama running, `llama3.2` pulled):\n")
w("       AIEV_MODEL=ollama:llama3.2 python3 vol3/runs/grading/ch11_k_sweep.py\n")
w("   Writes `vol3/runs/<date>-llama3.2-ch11-ksweep.txt` and `...-ch11-ksweep-sheet.csv` (60 rows, grade blank). For a single fresh sweep of all k instead: `AIEV_KS=2,3,4,5,6,7,8,9,10 AIEV_MODEL=ollama:llama3.2 python3 vol3/runs/grading/ch11_k_sweep.py`. The helper must be copied to the Mac clone first (it is only in the box clone, uncommitted).")
w("2. **Ch 16, 9 of 16 BENCH cases.** No command exists: these cases have no fixture question or evidence, so `real_runs.py` skips them. Someone must first write a question + fixture passages + expected answer for each of the 9 in `bench_cases()`; then `AIEV_MODEL=ollama:llama3.2 python3 vol3/runs/real_runs.py` (it reruns all chapters; logs carry the date). Until then, mark 3 can only report 7 of 16 and no `gate()` verdict.\n")
w("## Proposed replacement sentences (strict numbers; not applied)\n")
w("**Mark 1, ch11-context-assembly.md ~line 167** (replace \"answer accuracy per k with a recorded model is [TO MEASURE].\"):\n")
w("> answer accuracy per k is a separate number. With `llama3.2` (seed 7, temperature 0) on the six held-out questions, graded strictly by hand, it was 2/6 at k=2, 1/6 at k=3, 3/6 at k=5 and 1/6 at k=10; with one unrelated passage added to each pack it was 1/6, 0/6, 0/6 and 0/6. Coverage went from 3/6 to 4/6 and stayed flat; accuracy did not follow it.\n")
w("Also: the figure ch11-mm151-coverage-vs-k (alt text line 172) still shows ACCURACY as 'TO MEASURE' and needs new art or alt text.\n")
w("**Mark 2, ch11 ~line 220** (Expected output of Exercise: Sweep k):\n")
w("> Accuracy per k is a model experiment, graded by hand: our `llama3.2` run scored 2/6, 1/6, 3/6 and 1/6 at k = 2, 3, 5 and 10 (sheet in `vol3/runs/grading/`).\n")
w("(If the k = 4, 6-9 sweep is run first, replace with the full 2..10 row.)\n")
w("**Mark 3, ch16-rag-test-sets-and-regression-gates.md ~line 168:**\n")
w("> One `llama3.2` run (seed 7, temperature 0, Oct 27, 2026) on the 7 of 16 cases that have fixture evidence, graded by hand (sheet in `vol3/runs/grading/`): 5 of 7 replies were right in content, but the citation check escalated four uncited replies, so the pipeline answered 2 of 5 answerable cases, abstained on both expected abstains, sent one wrong answer (bundle-charger), and failed the critical cases eu-withdrawal and old-vs-new-window by escalating correct answers. The other 9 cases need fixture evidence before `gate()` can be run.\n")
w("## Per-case sheet (all 55 rows)\n")
w("| ch | case | k | dist | action | strict | lenient | borderline | reason | reply |\n|---|---|---|---|---|---|---|---|---|---|")
for o in S:
    w(f"| {o['chapter']} | {o['case']} | {o['k']} | {o['distractor']} | {o['action']} | {o['strict_grade']} | {o['lenient_grade']} | {o['borderline']} | {esc(o['reason'])}; {esc(o['citation_note'])} | {short(o['reply'])} |")
w("\n## Files\n")
w("- `/workspace/aev-code/vol3/runs/grading/2026-10-28-llama3.2-strict-grading.csv` (full replies, all columns)")
w("- `/workspace/aev-code/vol3/runs/grading/2026-10-28-llama3.2-strict-grading.md` (this file)")
w("- `/workspace/aev-code/vol3/runs/grading/build_grading.py` (grades as data; rebuilds the CSV), `build_md.py` (rebuilds this file)")
w("- `/workspace/aev-code/vol3/runs/grading/ch11_k_sweep.py` (missing-k run helper)")
w("- Copy: `/workspace/ebooks-mono/series/vol3-grading-2026-10-28.md`")
w("- Earlier lenient draft (Oct 27, other agent): `/workspace/vol3-runs/grading-proposed.csv`; 16 rows differ, mostly where this sheet counts invented extras as wrong.")
(H / "2026-10-28-llama3.2-strict-grading.md").write_text("\n".join(L) + "\n")
print("ok")

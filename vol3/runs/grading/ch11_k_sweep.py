"""Ch 11 accuracy-per-k: the k values the 2026-10-27 run did not record (4, 6, 7, 8, 9).

    AIEV_MODEL=ollama:llama3.2 python3 vol3/runs/grading/ch11_k_sweep.py

Same packs, prompt, model settings and distractor as real_runs.py ch11(); only the k list
differs (AIEV_KS, default "4,6,7,8,9"; use "2,3,4,5,6,7,8,9,10" for a full fresh sweep).
Writes vol3/runs/<date>-<model>-ch11-ksweep.txt and <date>-<model>-ch11-ksweep-sheet.csv
with blank grade columns. Nothing is graded here.
"""
import contextlib
import csv
import io
import os
import sys
from pathlib import Path

RUNS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RUNS))
import real_runs as RR  # noqa: E402  (also sets up _root, the Ollama meter, A, R)

KS = [int(x) for x in os.environ.get("AIEV_KS", "4,6,7,8,9").split(",")]


def sweep(sheet):
    RR.header("Ch 11 k-sweep", f"  ks={KS}")
    for dist in (False, True):
        for k in KS:
            for n, (q, need) in enumerate(RR.A.HELD_OUT, 1):
                pack = RR.A.pack_for(q, k)
                if dist:
                    pack = pack + [(f"S{len(pack) + 1}",
                                    dict(id=RR.DISTRACTOR, source="manual", score=0.0,
                                         text=RR.R.CHUNKS[RR.DISTRACTOR]))]
                action, reply = RR.A.answer(q, pack)
                ok, _, _ = RR.A.validate_citations(reply, pack)
                ids = [p["id"] for _, p in pack]
                covered = need <= set(ids)
                print(f"  k={k:<2} distractor={'yes' if dist else 'no '} q{n} covered={covered} "
                      f"citations_in_pack={ok} -> {action}")
                print(f"     reply: {reply}")
                sheet.append(dict(
                    chapter="11", case=f"q{n}", k=k, distractor="yes" if dist else "no",
                    question=q,
                    needed_passages=" | ".join(f"{i}: {RR.R.CHUNKS[i]}" for i in sorted(need)),
                    pack_ids=" ".join(ids), needed_in_pack="yes" if covered else "no",
                    citations_in_pack="yes" if ok else "no", reply=reply))


def main():
    sheet, buf = [], io.StringIO()
    with contextlib.redirect_stdout(buf):
        sweep(sheet)
    log = RR.OUT / f"{RR.DATE}-{RR.TAG}-ch11-ksweep.txt"
    log.write_text(buf.getvalue())
    out = RR.OUT / f"{RR.DATE}-{RR.TAG}-ch11-ksweep-sheet.csv"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, RR.FIELDS)
        w.writeheader()
        for row in sheet:
            w.writerow({**row, "grade": "", "grader": "", "notes": ""})
    print(f"wrote {log}\nwrote {out} ({len(sheet)} rows; grade by hand)")


if __name__ == "__main__":
    main()

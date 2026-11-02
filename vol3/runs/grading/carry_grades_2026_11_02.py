"""Carry the hand grades onto the 2026-11-02 re-run (code tag vol3-ed1, commit 0bec076).

    python3 vol3/runs/grading/carry_grades_2026_11_02.py

Every Ch 11 k-sweep reply (108) and every Ch 16 reply (15) of the Nov 2 run is
byte-identical to the Oct 31 run, and so are the packs and citation checks. This script
CHECKS that, row by row, against the blank Nov 2 sheets, and only then copies the final
Oct 31 grades (Prateek's review, Nov 1) into the Nov 2 graded sheets, naming the source
in `grade_source`. If any reply differs it stops: that row has to be graded by hand.
Then it prints the Ch 11 per-k table and the Ch 16 gate on the Nov 2 graded sheet.
"""
import csv
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent
PAIRS = [  # (blank Nov 2 sheet, final Oct 31 graded sheet, Nov 2 graded sheet)
    (RUNS / "2026-11-02-llama3.2-ch11-ksweep-sheet.csv",
     HERE / "2026-10-31-llama3.2-ch11-ksweep-graded.csv",
     HERE / "2026-11-02-llama3.2-ch11-ksweep-graded.csv"),
    (RUNS / "2026-11-02-llama3.2-grading-sheet-ch16.csv",
     HERE / "2026-10-31-llama3.2-ch16-graded.csv",
     HERE / "2026-11-02-llama3.2-ch16-graded.csv"),
]
GRADED = {"grade", "grader", "notes", "lenient", "borderline", "grade_source", "action",
          "labelled_by", "reviewed_by", "review_date", "changed"}
SOURCE = ("reused from the 2026-10-31 graded sheet (final grade after Prateek's 2026-11-01 "
          "review); Nov 2 reply byte-identical, checked by carry_grades_2026_11_02.py")


def key(r):
    return (r["chapter"], r["case"], r["k"], r["distractor"])


def carry(blank, old, out):
    new = list(csv.DictReader(blank.open(newline="")))
    prev = {key(r): r for r in csv.DictReader(old.open(newline=""))}
    assert len(new) == len(prev), (blank.name, len(new), len(prev))
    rows = []
    for r in new:
        o = prev[key(r)]
        for col, v in r.items():
            if col in GRADED:
                continue
            if o.get(col) != v:
                sys.exit(f"{blank.name} {key(r)}: {col} differs from Oct 31; grade by hand")
        rows.append({**o, "grade_source": SOURCE})
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out.name} ({len(rows)} rows, all replies byte-identical to Oct 31)")
    return rows


def main():
    ch11 = carry(*PAIRS[0])
    carry(*PAIRS[1])
    ks = sorted({int(r["k"]) for r in ch11})
    print("Ch 11 correct (strict) per k  " + " ".join(f"{k:>3}" for k in ks))
    for dist, lab in (("no", "without extra passage"), ("yes", "with extra passage   ")):
        cells = [sum(r["grade"] == "correct" for r in ch11
                     if int(r["k"]) == k and r["distractor"] == dist) for k in ks]
        print(f"  {lab}        " + " ".join(f"{c:>3}" for c in cells))
    print("Ch 16 gate on the Nov 2 graded sheet:", flush=True)
    subprocess.run([sys.executable, str(HERE / "gate_from_sheet.py"), str(PAIRS[1][2])], check=True)


if __name__ == "__main__":
    main()

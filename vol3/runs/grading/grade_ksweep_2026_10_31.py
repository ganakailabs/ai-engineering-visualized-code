"""Strict hand grades for the 2026-10-31 llama3.2 Ch 11 k-sweep (k = 2..10).

Same rubric as 2026-10-28-llama3.2-strict-grading.md. The 48 replies at k = 2, 3, 5, 10
are byte-identical to the 2026-10-27 run, so their Oct 28 grades are reused; the 60 new
replies (k = 4, 6, 7, 8, 9) are graded below. Writes
2026-10-31-llama3.2-ch11-ksweep-graded.csv and prints the per-k table.
    python3 vol3/runs/grading/grade_ksweep_2026_10_31.py
"""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent
SHEET = RUNS / "2026-10-31-llama3.2-ch11-ksweep-sheet.csv"
OLD = HERE / "2026-10-28-llama3.2-strict-grading.csv"
OUT = HERE / "2026-10-31-llama3.2-ch11-ksweep-graded.csv"

# (case, k, distractor) -> (strict, lenient, borderline, reason)
NEW = {
 ("q1", 4, "yes"): ("wrong", "wrong", "no", "gives 2 days and 21 days as return windows beside 30 days"),
 ("q1", 6, "no"): ("wrong", "correct", "yes", "30 days stated, prefixed 'varies depending on the type of return' (as Oct 28 q1 k=5 dist)"),
 ("q1", 6, "yes"): ("wrong", "correct", "yes", "30 days stated, then 'However, international returns take 21 days' (transit, not a window)"),
 ("q1", 7, "no"): ("wrong", "wrong", "no", "2-day and 21-day 'return windows' again"),
 ("q1", 8, "no"): ("wrong", "wrong", "no", "2-day and 21-day 'return windows' again"),
 ("q1", 8, "yes"): ("wrong", "wrong", "no", "2-day and 21-day 'return windows' again"),
 ("q1", 9, "no"): ("wrong", "wrong", "no", "'varies'; 2-day and 21-day presented as windows"),
 ("q2", 4, "no"): ("wrong", "correct", "yes", "photo within 7 days right; adds the 21-day international transit (implies shipping back)"),
 ("q2", 4, "yes"): ("wrong", "correct", "yes", "photo within 7 days right; adds the 21-day international transit"),
 ("q2", 6, "no"): ("wrong", "correct", "yes", "photo right; 'proceed with the return process' plus 21-day transit"),
 ("q2", 6, "yes"): ("wrong", "correct", "yes", "photo right; misuse speculation (mug-care) and a 30-day return (as Oct 28 q2 k=3 dist)"),
 ("q2", 7, "no"): ("wrong", "correct", "yes", "photo right; 'follow the standard return process and contact customer service' not in pack"),
 ("q2", 7, "yes"): ("wrong", "correct", "yes", "photo right; return process + documentation not in pack (as Oct 28 q2 k=5 dist)"),
 ("q2", 8, "no"): ("wrong", "correct", "yes", "photo right; 'return window may vary by location' and 21-day transit"),
 ("q2", 8, "yes"): ("correct", "correct", "yes", "photo within 7 days [S2]; 'check the return policy for any additional requirements' is a hedge, not a claim"),
 ("q2", 9, "no"): ("correct", "correct", "yes", "same reply as k=8 distractor"),
 ("q3", 4, "no"): ("correct", "correct", "no", "No, final sale (as Oct 28 q3 k=2)"),
 ("q3", 4, "yes"): ("abstained", "abstained", "no", "'implies returns may not be accepted'; never commits"),
 ("q3", 6, "no"): ("abstained", "abstained", "no", "'implying returns may not be accepted'; never commits"),
 ("q3", 6, "yes"): ("wrong", "correct", "yes", "not returnable [S2] right; invents 'not available in other sizes' from jacket-size"),
 ("q3", 7, "no"): ("correct", "correct", "yes", "commits: not returnable, final sale [S2]; 'no direct information' is a hedge (ret-final not in pack); no 'or exchanges' as in Oct 28 q3 k=3 dist"),
 ("q3", 7, "yes"): ("correct", "correct", "yes", "same reply as k=7 no distractor"),
 ("q3", 8, "no"): ("correct", "correct", "yes", "same reply as k=7 no distractor"),
 ("q3", 8, "yes"): ("wrong", "correct", "yes", "adds 'or exchanges' (as Oct 28 q3 k=3 dist)"),
 ("q3", 9, "no"): ("correct", "correct", "yes", "commits: not returnable, final sale [S2]; adds a remark on the pack, no false claim"),
 ("q3", 9, "yes"): ("abstained", "abstained", "no", "truncated before any answer (as Oct 28 q3 k=10)"),
 ("q4", 4, "no"): ("wrong", "wrong", "no", "answers No from ret-intl; pay-cod never retrieved"),
 ("q4", 4, "yes"): ("wrong", "wrong", "no", "answers No from ret-intl"),
 ("q4", 6, "no"): ("wrong", "wrong", "no", "answers No from ret-intl"),
 ("q4", 7, "no"): ("wrong", "wrong", "no", "answers No from ret-intl"),
 ("q4", 7, "yes"): ("wrong", "wrong", "no", "answers No from ret-intl"),
 ("q4", 8, "no"): ("wrong", "wrong", "no", "answers No from ret-intl"),
 ("q4", 8, "yes"): ("wrong", "wrong", "no", "answers No from ret-intl"),
 ("q5", 4, "no"): ("wrong", "correct", "yes", "5-7 days given, but 'may vary depending on the return type' and 'refund will not reach the card' for final sale"),
 ("q5", 4, "yes"): ("wrong", "wrong", "no", "says there is no refund timing for the payment method (pay-refund is S1) and invents 'damaged refunds processed within 7 days'"),
 ("q5", 6, "yes"): ("abstained", "abstained", "no", "says the timing is not specified"),
 ("q5", 7, "no"): ("correct", "correct", "yes", "5-7 days to the original payment method [S1]; then lists other passages accurately"),
 ("q5", 7, "yes"): ("correct", "correct", "yes", "commits to 5-7 days [S1] after 'no direct answer'; 'exact timing may vary' is a hedge"),
 ("q5", 8, "no"): ("correct", "correct", "yes", "5-7 days [S1]; then lists other passages accurately"),
 ("q5", 8, "yes"): ("abstained", "abstained", "no", "says the timeframe cannot be determined"),
 ("q5", 9, "no"): ("correct", "correct", "yes", "5-7 days [S1]; then lists other passages accurately"),
 ("q5", 9, "yes"): ("abstained", "abstained", "no", "quotes 5-7 days without committing (as Oct 28 q5 k=10 dist)"),
 ("q6", 4, "no"): ("wrong", "wrong", "no", "'follow steps S1 and S2' without stating order number or photo"),
 ("q6", 4, "yes"): ("wrong", "correct", "yes", "order number + photo, but 'to the manufacturer' and says it is unclear whether replacement is free"),
 ("q6", 6, "no"): ("wrong", "wrong", "no", "'follow steps S1 and S2' without stating them"),
 ("q6", 7, "no"): ("wrong", "correct", "yes", "order number + photo + 12 months, but 'to the manufacturer' and invented steps (pair first, reset)"),
 ("q6", 7, "yes"): ("wrong", "correct", "yes", "'to the manufacturer', 'unclear' if free, reset/return steps"),
 ("q6", 8, "yes"): ("wrong", "correct", "no", "order number + photo only; the 12-month free replacement is missing"),
 ("q6", 9, "yes"): ("correct", "correct", "no", "free within 12 months [S1]; order number + photo [S2]"),
}


def main():
    old = {r["reply"]: r for r in csv.DictReader(OLD.open()) if r["chapter"] == "11"}
    rows = list(csv.DictReader(SHEET.open()))
    out = []
    for r in rows:
        key = (r["case"], int(r["k"]), r["distractor"])
        if key in NEW:
            s, l, b, why = NEW[key]
            src = "graded 2026-10-31"
        else:
            o = old[r["reply"]]          # KeyError = an ungraded reply; fail loudly
            s, l, b, why = o["strict_grade"], o["lenient_grade"], o["borderline"], o["reason"]
            src = f"reused: identical reply, Oct 28 grade of {o['case']} k={o['k']} dist={o['distractor']}"
        out.append({**r, "grade": s, "grader": "Grok Bot (strict rubric)", "notes": why,
                    "lenient": l, "borderline": b, "grade_source": src})
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, list(out[0]))
        w.writeheader()
        w.writerows(out)
    ks = sorted({int(r["k"]) for r in out})
    print("k        " + " ".join(f"{k:>4}" for k in ks))
    for dist in ("no", "yes"):
        for col, lab in (("needed_in_pack", "coverage"), ("grade", "strict"), ("lenient", "lenient")):
            want = "yes" if col == "needed_in_pack" else "correct"
            cells = []
            for k in ks:
                sel = [r for r in out if int(r["k"]) == k and r["distractor"] == dist]
                cells.append(f"{sum(r[col] == want for r in sel)}/{len(sel)}")
            print(f"{lab:<9}{'+d' if dist == 'yes' else '  '} " + " ".join(f"{c:>4}" for c in cells))
    print(f"wrote {OUT} ({len(out)} rows; {sum(r['borderline'] == 'yes' for r in out)} borderline)")


if __name__ == "__main__":
    main()

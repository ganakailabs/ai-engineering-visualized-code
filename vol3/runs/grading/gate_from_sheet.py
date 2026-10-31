"""Strict hand grades for the 2026-10-31 llama3.2 Ch 16 run (15 of 16 BENCH cases) and
the regression gate run on them.

    python3 vol3/runs/grading/gate_from_sheet.py

Grades: same rubric as 2026-10-28-llama3.2-strict-grading.md (Grok Bot draft for
Prateek's review; borderline calls flagged). The 7 replies also in the morning's
7-case run are byte-identical and keep their grades. Writes
2026-10-31-llama3.2-ch16-graded.csv and prints the gate.

Two readings of one run, both printed:
  end-to-end : what the customer would get. An answerable case passes only if the
               reply was SENT and graded correct; an unanswerable case passes if no
               reply was sent (escalated). abstained = not sent.
  content    : the reply text alone, ignoring the citation check. Answerable passes
               if graded correct; unanswerable passes only if graded abstained.
The baseline is gate.results("baseline"), the chapter's SCRIPTED baseline, not a
real-model run. bundle-stand has no grounded fixture and is not run, so the full
16-case gate blocks on a missing case by design; the 15-case gate is also printed.
"""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent
sys.path.insert(0, str(RUNS.parent))
import _root  # noqa: E402,F401
import gate as G  # noqa: E402

SHEET = RUNS / "2026-10-31-llama3.2-grading-sheet-ch16.csv"
OUT = HERE / "2026-10-31-llama3.2-ch16-graded.csv"

# case -> (strict grade, borderline, reason)
GRADES = {
 "eu-withdrawal": ("correct", "no", "14 days from delivery, no reason: matches S5; no [Sn] labels -> escalated (critical answerable case not answered)"),
 "in-battery-row": ("wrong", "yes", "12 months in India, claim by email: right; adds 'along with the receipt' (the sheet says keep the receipt, not send it); never says a battery that stops charging is a defect, only 'covered'; no labels -> escalated"),
 "old-vs-new-window": ("correct", "no", "30 days: matches kept R1@2026-09-15; no labels -> escalated (critical)"),
 "refund-vs-ticket": ("correct", "no", "No, 30 days not 7 [S1]: precedence kept R1@2026-09-15; sent"),
 "supplier-vs-policy": ("correct", "yes", "No, 30 days [S1]; rejects the 90-day supplier page [S2], but its reason ('not a direct statement from the seller or manufacturer') is the model's own; sent"),
 "other-tenant-note": ("correct", "no", "No: photo required [S2], within 7 days [S1]; Southpeak's VIP no-photo note was filtered out and not echoed; sent"),
 "internal-only-page": ("correct", "no", "photo of the damage [S1], within 7 days [S2]; nothing from the internal Rs 20,000 note; sent"),
 "revoked-page": ("correct", "yes", "'free under warranty' [S1]: the page says 'under warranty'; 'free' is the model's gloss; the restricted NW-550 'paid service' page was not in the pack; sent"),
 "retired-clause": ("correct", "no", "No, 30 days now [S1]; retired June and future November clauses dropped by precedence; sent"),
 "stale-order-total": ("correct", "no", "INR 950, delivered 2026-10-01 from the live record; ignored the 'in transit' snapshot; no labels -> escalated"),
 "bundle-charger": ("correct", "no", "Yes, covered: both needed edges in the pack; no labels -> escalated"),
 "final-sale-refund": ("correct", "no", "No refund, final sale [S2]; ret-final not in pack, inference is the model's (as Oct 28); sent"),
 "gift-card-cash": ("wrong", "yes", "expected abstain (no gift-card rule passes the Ch 4 gate); answers 'No, you cannot' while admitting the handbook says nothing; true elsewhere in the book (S4), unsupported by this pack; (S3) not a label -> escalated, so not sent"),
 "lifetime-warranty": ("abstained", "no", "no direct information on a lifetime warranty; 12-month battery note is true; expected abstain: right; (S1) not a label -> escalated"),
 "unknown-part": ("wrong", "no", "claims the cable is covered as part of the bundle; no edge puts the cable in the bundle; expected unknown; escalated (no labels), so the wrong reply was not sent"),
}


def load():
    rows = list(csv.DictReader(SHEET.open()))
    for r in rows:
        g, b, why = GRADES[r["case"]]
        r.update(grade=g, grader="Grok Bot (strict, draft for Prateek's review)",
                 notes=f"{'BORDERLINE: ' if b == 'yes' else ''}{why}",
                 action="send" if r["citations_in_pack"] == "yes" else "escalate")
        r["borderline"] = b
    return rows


def records(rows, reading):
    ans = {c: a for c, _, a, _ in G.BENCH}
    out = {}
    for r in rows:
        c, sent, g = r["case"], r["action"] == "send", r["grade"]
        if reading == "end-to-end":
            out[c] = ((sent and g == "correct") if ans[c] else not sent, not sent)
        else:
            out[c] = ((g == "correct") if ans[c] else g == "abstained", g == "abstained")
    return out


def show(name, g):
    print(f"  {name}: {g['label']}")
    for why in g["reasons"]:
        print(f"      - {why}")
    if not g.get("missing"):
        print(f"      answered {g['answered']}/{g['answerable']}  abstained "
              f"{g['abstained']}/{g['expected_abstain']}  critical failures: "
              f"{', '.join(g['critical']) or 'none'}  new failures vs baseline: "
              f"{', '.join(g['new_failures']) or 'none'}")


def main():
    rows = load()
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT} ({len(rows)} rows)")
    run = {r["case"] for r in rows}
    bench15 = [b for b in G.BENCH if b[0] in run]
    base = G.results("baseline")
    for reading in ("end-to-end", "content"):
        new = records(rows, reading)
        print(f"{reading}:")
        show("16-case BENCH", G.gate_results(base, new))
        show(f"{len(bench15)}-case BENCH (bundle-stand not grounded)",
             G.gate_results(base, new, bench15))


if __name__ == "__main__":
    main()

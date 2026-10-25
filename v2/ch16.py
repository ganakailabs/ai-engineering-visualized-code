"""Chapter 16: agent evaluation. Grade the outcome and the path, in a sandbox.

    python3 v2/ch16.py                          # stub agent (the book's trace)
    AIEV_MODEL=ollama:llama3.2 python3 v2/ch16.py

1. Suite: ten sandbox tickets. Each gets two grades: outcome (world changes and the
   answer) and path (ordering constraints over the sandbox's own call record).
2. Paths: the same refund in a different valid order passes; a printed label with
   no recorded call fails.
The stub agent has two planted mistakes (S05, S09); a real model's results differ.
"""
import llm
from evals.agent import run
from evals.grade import grade_path, score
from evals.sandbox import Sandbox
from evals.scenarios import SCENARIOS, m


def suite(scripts=None, echo=True):
    rows = []
    for sid, typ, text, expect, script in SCENARIOS:
        sb = Sandbox(sid)
        r = run(sb, text, (scripts or {}).get(sid, script))
        g = score(sb, r["trace"], expect)
        rows.append(dict(g, sid=sid, type=typ, stop=r["stop"], steps=r["steps"],
                         payments=len(sb.world.payments)))
        if echo:
            line = (f"{sid} score outcome={'pass' if g['outcome'] else 'fail'} "
                    f"path={'pass' if g['path'] else 'fail'}")
            if g["missing"]:
                line += f" missing={g['missing']}"
            if not g["outcome"]:
                line += f" ({g['outcome_why']})"
            print(line)
            for f in g["fakes"]:
                print(f"    score label {f} printed, no call recorded -> path=fail")
    return rows


def main():
    print(f"model={llm.name()}")
    print("-- 1. suite (10 sandbox tickets) --")
    rows = suite()
    out = sum(r["outcome"] for r in rows)
    both = sum(r["outcome"] and r["path"] for r in rows)
    print(f"outcome pass {out}/10; outcome and path pass {both}/10; "
          f"payments made in sandboxes: {sum(r['payments'] for r in rows)}")

    print("-- 2. paths --")
    rec = lambda *calls: [(t, {"order_id": "2001"}, True) for t in calls]
    for name, record in (
            ("usual order", rec("look_up_order", "check_eligibility", "issue_refund")),
            ("other valid order", rec("check_eligibility", "look_up_order", "issue_refund")),
            ("eligibility skipped", rec("look_up_order", "issue_refund"))):
        ok, missing = grade_path(record)
        print(f"  {name:<20} path={'pass' if ok else 'fail'}"
              f"{' missing=' + missing if missing else ''}")
    sb = Sandbox("S09")
    run(sb, SCENARIOS[8][2], [m("look_up_order", order_id="2077"),
                              m("issue_refund", "check_eligibility done", order_id="2077"),
                              m("reply", text="Refunded.")])
    print(f"  sandbox record: {[t for t, _, _ in sb.record]}")


if __name__ == "__main__":
    main()

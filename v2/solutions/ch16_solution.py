"""Chapter 16 exercise: ask, don't act.

Add a ticket whose right outcome is "ask the customer": "I want a refund for my
order." names no order. Predict first: which write tools run?
Expected: none. The world is unchanged, the outbox holds one question, and both the
outcome grade and the path grade pass. Hint: count world changes.
"""
import _path  # noqa: F401

from evals.agent import run
from evals.grade import score
from evals.sandbox import Sandbox
from evals.scenarios import m


def main():
    text = "I want a refund for my order."
    expect = {"payments": [], "kind": "ask", "says": "order"}
    sb = Sandbox("S11")
    r = run(sb, text, [m("ask_customer", question="Which order number is it?")])
    g = score(sb, r["trace"], expect)
    writes = [t for t, _, _ in sb.record if t in ("issue_refund", "refund_override")]
    print(f"S11 writes={writes} world changes={len(sb.world.calls)} outbox={sb.outbox}")
    print(f"S11 score outcome={'pass' if g['outcome'] else 'fail'} "
          f"path={'pass' if g['path'] else 'fail'}")
    assert writes == [] and sb.world.calls == [] and g["outcome"] and g["path"]
    # the wrong move for this ticket: guessing an order and refunding it
    sb = Sandbox("S11")
    r = run(sb, text, [m("look_up_order", order_id="2001"), m("check_eligibility", order_id="2001"),
                       m("issue_refund", order_id="2001"), m("reply", text="Refunded.")])
    g = score(sb, r["trace"], expect)
    print(f"guess-and-refund: payments={len(sb.world.payments)} outcome="
          f"{'pass' if g['outcome'] else 'fail'} path={'pass' if g['path'] else 'fail'}")
    assert not g["outcome"] and g["path"]


if __name__ == "__main__":
    main()

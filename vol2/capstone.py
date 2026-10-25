"""Capstone: one support ticket through the Vol 2 boundaries, end to end.

Order #3100's refund (INR 12,500) sits in the APPROVE band. The assistant:
  1. reads the current policy grid (Ch 8) and holds the action for a person;
  2. gets a stored, authorised approval and commits it through the crash-safe
     ledger (Ch 6), so a replay of the same operation pays exactly once;
  3. refuses a forged approval for a HUMAN_ONLY amount and hands off a full card (Ch 8);
  4. releases only if the reliability gate passes on complete evidence (Ch 17).
Stub model only; run from the repo root:  python3 vol2/capstone.py
"""
import _root  # noqa: F401

import approvals
import ch08
import ch17
from harness import Session
from ledger import Ledger
from world import World, WorldError

SESSION = Session("c-42")


def refund_once(world, ledger, action, approval, op_id):
    def call(key):
        r = approvals.commit(world, SESSION, action,
                             approval, key=key)
        if not r["ok"]:
            raise WorldError(r["error"])
        return r["receipt"]["receipt_id"]
    args = {"order_id": action["order_id"],
            "amount": action["amount"]}
    return ledger.execute(
        op_id, args, call,
        lambda key: (world.find_payment(key) or {}).get(
            "receipt_id"))

def main():
    world, ledger = World(), Ledger()
    action = ch08.refund_action(world, "3100")
    print(f"1. policy  #3100 INR {action['amount']:,} -> {approvals.grid(action)}")

    apv = approvals.approve(world, action, "sup-meera")
    first = refund_once(world, ledger, action, apv, "op-3100-refund")
    again = refund_once(world, ledger, action, apv, "op-3100-refund")   # a replayed step
    print(f"2. commit  {first['state']} receipt={first['receipt']}; replay -> "
          f"{again['state']} receipt={again['receipt']}; "
          f"payments={len(world.payments_for('3100'))}")

    big = World()
    big.edit_order("3100", amount=60000)
    act60 = ch08.refund_action(big, "3100")
    forged = approvals.approve(big, act60, "anyone")
    r = approvals.commit(big, SESSION, act60, forged, key="k-60k")
    card = approvals.handoff(summary="refund INR 60,000 for #3100",
                             evidence="order #3100, amount above the approval band",
                             proposed_action="refund INR 60,000",
                             done_so_far="nothing executed")
    print(f"3. refuse  INR 60,000 -> {r['error']}; payments={len(big.payments_for('3100'))}; "
          f"handoff fields={len(card)}")

    rows = ch17.trials(1)
    released = ch17.gate(rows, "agent")
    print(f"4. gate    rows={len(rows)} -> {'release' if released else 'hold'}; "
          f"empty evidence -> {'release' if ch17.gate([], 'empty') else 'hold'}")
    return first, again, r, released


if __name__ == "__main__":
    main()

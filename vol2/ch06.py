"""Chapter 6: Side Effects: Idempotency, Transactions and Compensation.

Run from the repo root:  python3 vol2/ch06.py
Real model (optional):  AIEV_MODEL=ollama:llama3.2 python3 vol2/ch06.py
Parts 1-4 are scripted faults in the mock world (demonstrations). In part 5 the model
proposes the refund; the ledger's guarantee must not depend on what it proposes.
"""
import json
import os
import tempfile

import ledger
import llm
from events import Trace
from world import World, WorldError

OP, ARGS = "op-refund-2001-T-2001-a", {"order_id": "2001", "amount": 950}


def refund_call(world):
    return lambda key: world.refund("2001", 950, key=key)


def timeout_retry_break():
    print("--- 1. BREAK: a timeout retried with a new key (scripted) ---")
    world = World(faults={"refund": ["LOST_REPLY"]})
    tr = Trace(world, "T-2001-a", "asha")
    for attempt, key in ((1, "k-attempt-1"), (2, "k-attempt-2")):
        try:
            world.refund("2001", 950, key=key)
            tr.emit("act", f"refund key={key} -> paid")
        except WorldError as e:
            tr.emit("observe", f"refund key={key} -> {e.code}; retrying")
    tr.emit("observe", f"payments for #2001: {len(world.payments_for('2001'))}")
    return world


def ledger_fix():
    print("--- 2. FIX: the ledger, a lost reply, a second worker, a restart (scripted) ---")
    path = os.path.join(tempfile.mkdtemp(), "ledger.db")
    world = World(faults={"refund": ["LOST_REPLY"]})
    tr = Trace(world, "T-2001-a", "asha")
    worker1, worker2 = ledger.Ledger(path), ledger.Ledger(path)
    row = worker1.prepare(OP, ARGS)
    tr.emit("ledger", f"op={OP} PREPARED key={row['key']}")

    def call(key):                              # worker2 tries while worker1 waits
        tr.emit("ledger", "SUBMITTED")
        other = worker2.execute(OP, ARGS, refund_call(world), world.find_payment)
        tr.emit("check", f"worker2 same op -> {other['state']}, not sent again")
        return world.refund("2001", 950, key=key)
    row = worker1.execute(OP, ARGS, call, world.find_payment)
    tr.emit("observe", f"{row['error']} -> {row['state']}")
    restarted = ledger.Ledger(path)             # the process restarts
    row = restarted.reconcile(OP, world.find_payment)
    tr.emit("reconcile", f"key={row['key']} found receipt={row['receipt']['receipt_id']} "
            f"-> {row['state']}")
    try:
        restarted.execute(OP, dict(ARGS, amount=9500), refund_call(world), world.find_payment)
    except ledger.ArgsChanged:
        tr.emit("check", "same op, other args -> refused")
    again = worker2.execute(OP, ARGS, refund_call(world), world.find_payment)
    tr.emit("ledger", f"worker2 retry -> same receipt {again['receipt']['receipt_id']}")
    tr.emit("observe", f"payments for #2001: {len(world.payments_for('2001'))}")
    return world, again


def expired_key(use_ledger):
    print(f"--- 3. the receiver forgets the key after 24 hours "
          f"({'FIX: reconcile first' if use_ledger else 'BREAK: blind retry'}) ---")
    world = World(faults={"refund": ["LOST_REPLY"]})
    book = ledger.Ledger()
    tr = Trace(world, "T-2001-a", "asha")
    row = book.execute(OP, ARGS, refund_call(world), world.find_payment)
    tr.emit("ledger", f"{row['error']} -> {row['state']}")
    world.tick(2 * 24 * 60)                     # two days pass on the simulated clock
    world.prune_keys(keep_hours=24)
    tr.emit("observe", "clock +2 days; receiver pruned keys older than 24 hours")
    if use_ledger:
        row = book.execute(OP, ARGS, refund_call(world), world.find_payment)
        tr.emit("reconcile", f"found in payments record -> {row['state']}")
    else:
        world.refund("2001", 950, key=row["key"])
        tr.emit("act", "retry with the same key -> paid (the key was forgotten)")
    tr.emit("observe", f"payments for #2001: {len(world.payments_for('2001'))}")
    return world


def compensation(fault=None):
    print(f"--- 4. compensation is a new action{' that fails' if fault else ''} (scripted) ---")
    world = World(faults={"cancel_pickup": [fault]} if fault else None)
    book = ledger.Ledger()
    tr = Trace(world, "T-2001-s", "asha")
    pick = book.execute("op-pickup-2001", {"order_id": "2001", "item": "mug set green"},
                        lambda key: world.book_pickup("2001", "mug set green", key=key),
                        lambda key: None)
    tr.emit("ledger", f"pickup {pick['receipt']['receipt_id']} -> {pick['state']}")
    rid = pick["receipt"]["receipt_id"]
    row = book.compensate("op-pickup-2001", lambda key: world.cancel_pickup(rid, key=key),
                          {"cancel": rid})
    tr.emit("ledger", f"cancel pickup -> {row['compensation']['state']}; "
            f"pickup op -> {row['state']}")
    pay = book.execute(OP, ARGS, refund_call(world), world.find_payment)
    paid = book.compensate(OP, None, {})
    tr.emit("ledger", f"refund {pay['receipt']['receipt_id']} cannot be undone -> "
            f"{paid['state']}")
    return world, book


SYSTEM = ("You handle one Northwind Goods refund ticket. Tool: issue_refund(order_id). "
          "The amount is always the order total. Reply with ONE JSON object and nothing "
          'else: {"action": "issue_refund", "args": {"order_id": "2001"}} or '
          '{"final": "<short reply to the customer>"}')
TICKET = "Ticket: My ceramic mug set #2001 arrived cracked. I sent a photo. Refund please."


def stub(user):
    if "Result:" not in user:
        return {"action": "issue_refund", "args": {"order_id": "2001"}}
    return {"final": "Your refund of INR 950 is on its way."}


def model_drives():
    print(f"--- 5. the model proposes, the ledger executes (model={llm.name()}) ---")
    path = os.path.join(tempfile.mkdtemp(), "ledger.db")
    world = World(faults={"refund": ["LOST_REPLY"]})
    book = ledger.Ledger(path)
    tr = Trace(world, "T-2001-a", "asha", llm.name())
    context = TICKET
    for _ in range(4):
        move, _ = llm.ask_json(SYSTEM, context, stub)
        if not isinstance(move, dict) or "final" in move:
            done = [r for r in book.db.execute("SELECT state FROM ops")] == [("CONFIRMED",)]
            reply = str((move or {}).get("final", "escalate: no valid move"))
            if not done:     # a reply may not claim money the ledger does not show
                tr.emit("check", f"final reply without a CONFIRMED refund: {reply!r}")
                reply = "escalate: no confirmed refund in the ledger; a person follows up"
            tr.emit("reply", reply)
            break
        oid = str((move.get("args") or {}).get("order_id", "")).lstrip("#")
        tr.emit("propose", f"{move.get('action')} order={oid}", actor="model")
        if move.get("action") != "issue_refund" or world.order(oid) is None \
                or world.order(oid)["owner"] != "asha":
            result = {"state": "REFUSED"}
        else:
            amount = world.order(oid)["amount"]
            result = book.execute(f"op-refund-{oid}-T-2001-a",
                                  {"order_id": oid, "amount": amount},
                                  lambda key: world.refund(oid, amount, key=key),
                                  world.find_payment)
            if result["state"] == "UNKNOWN":
                result = book.reconcile(f"op-refund-{oid}-T-2001-a", world.find_payment)
                tr.emit("reconcile", f"-> {result['state']}")
        tr.emit("ledger", f"state={result['state']}")
        context += f"\nYou proposed: {json.dumps(move)}\nResult: {json.dumps(result)}"
    tr.emit("observe", f"payments for #2001: {len(world.payments_for('2001'))}")
    return world, tr.events


if __name__ == "__main__":
    timeout_retry_break()
    ledger_fix()
    expired_key(False)
    expired_key(True)
    compensation()
    compensation("ALREADY_COLLECTED")
    model_drives()

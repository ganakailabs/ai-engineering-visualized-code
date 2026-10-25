"""Chapter 10: Context Engineering for Long-Running Agents.

Run from the repo root:  python3 vol2/ch10.py
Real model (optional):  AIEV_MODEL=ollama:llama3.2 python3 vol2/ch10.py
A 30-step dispute ticket (fixture data, fictional) on the shared mock world. At step 3
the refund's reply is lost, so the ledger row is UNKNOWN (Chapter 6). The model writes
the summary at each compaction and chooses the next action at step 30; the context it
is given is what we check. The stub summarizer is a scripted lossy summary (a
demonstration, not a model).
"""
import re

import context
import ledger
import llm
import state
from events import Trace
from world import World

TICKET, OP = "T-2001-a", "op-refund-2001-T-2001-a"
ARGS = {"order_id": "2001", "amount": 950}
BUDGET = 300                       # placeholder tokens per call (context.count)
STEPS = 30

NOTES = [  # fixture turns for steps 4-29 (fictional)
    "customer: I sent the photo yesterday, did you get it?",
    "look_up_order -> mug set, INR 950, delivered 2026-10-01",
    "customer: the box was also wet when it arrived",
    "courier note: parcel left at the gate, no signature",
    "customer: can you tell me when the money comes back?",
    "agent: told the customer we are checking the payment",
    "customer: my bank app shows nothing yet",
    "courier note: driver reports the box was dropped once",
    "customer: I also want to complain about the courier",
    "agent: logged a courier complaint, ref CC-77",
    "customer: please do not send another mug set",
    "customer: is the green one in stock anyway?",
    "check_stock -> mug set green 4",
    "customer: never mind, refund is fine",
    "customer: I am travelling next week, email only please",
    "agent: noted email-only contact",
    "customer: any update?",
    "courier: complaint CC-77 acknowledged",
    "customer: the wet box ruined my table cloth too",
    "agent: told the customer the table cloth is outside the order",
    "customer: fine. just the refund then",
    "customer: hello?",
    "agent: apologised for the wait",
    "customer: my sister had the same problem last month",
    "customer: ok I will wait for the refund",
    "customer: still nothing in my bank, what now?",
]

SUM_SYSTEM = ("You compress a support ticket's history. Reply with ONE JSON object and "
              'nothing else: {"summary": "<at most 40 words>"}')
DECIDE_SYSTEM = ("You are the Northwind Goods support agent on a long ticket. Choose the "
                 "next action from the context only. Reply with ONE JSON object and "
                 'nothing else: {"action": "reconcile" or "issue_refund" or '
                 '"reply_customer", "order_id": "<order id, or empty if unknown>"}')


def stub_summary(user):
    """Scripted lossy summary: the gist survives, the ids and the UNKNOWN do not."""
    return {"summary": "Customer's mug set arrived cracked and wet; photo received; "
                       "a refund was attempted; customer is waiting for the money."}


def stub_decide(user):
    order = re.search(r"order: (\d+)|#(\d+)", user)
    order = next((g for g in order.groups() if g), "") if order else ""
    if "UNKNOWN" in user:
        return {"action": "reconcile", "order_id": order}
    return {"action": "issue_refund", "order_id": order}


def pay(world):
    return lambda key: world.refund("2001", 950, key=key)


def find(world):
    """The payments system's record by key (Chapter 6 reconcile)."""
    return lambda key: (world.by_key.get(key) or (None, None, None))[2]


def summarize(previous, turns):
    text = (f"Earlier summary: {previous}\n" if previous else "") + "\n".join(turns)
    move, _ = llm.ask_json(SUM_SYSTEM, text, stub_summary, max_output_tokens=120)
    return str((move or {}).get("summary", previous))


def run(pinned=True, budget=BUDGET, steps=STEPS, echo=True):
    print(f"--- {'FIX: pins and obligations from state' if pinned else 'BREAK: history and summary only'}"
          f" (budget={budget}, model={llm.name()}) ---")
    world = World(faults={"refund": ["LOST_REPLY"]})
    tr = Trace(world, TICKET, "asha", model=llm.name(), echo=echo)
    session = {"customer_id": "asha"}                     # identity: the login session
    store, book = state.Store(), ledger.Ledger()
    store.create(TICKET, {"order_id": "2001"})
    v = store.move(TICKET, "VERIFYING", 1)
    v = store.move(TICKET, "ACTING", v, data={"verification": {
        "ok": True, "checks": ["owner", "R2 damaged within 7 days"]}})
    ctx = context.Context(budget, summarize, pinned=pinned)
    ctx.add("step 1 customer: My mug set #2001 arrived cracked. Refund please.")
    ctx.add("step 2 check: asha owns #2001; R2 damaged within 7 days; photo needed")
    row = book.execute(OP, ARGS, pay(world), find(world))
    ctx.add(f"step 3 act: issue_refund #2001 INR 950 -> {row.get('error')}; "
            f"ledger {OP} {row['state']}")
    log = []                                              # (step, tokens, pins, owed)
    for step in range(4, steps + 1):
        world.tick(30)
        if step < steps:
            ctx.add(f"step {step} {NOTES[(step - 4) % len(NOTES)]}")
        else:                                             # MM-105: only now, only R2
            ctx.add(f"step {step} decide: what next for this ticket?")
            ctx.load("R2")
            tr.emit("retrieve", "load manual section=R2 (just in time); up front would "
                    f"be 9 sections, {context.up_front_tokens()} tokens")
        pins, owed = context.project(session, store, book, TICKET, [OP])
        text, tokens, folded = ctx.fit(context.render_pins(pins, owed))
        kept_pins, kept_owed = context.survives(text, pins, owed)
        log.append({"step": step, "tokens": tokens, "pins": kept_pins,
                    "owed": kept_owed, "need_pins": len(pins), "need_owed": len(owed)})
        if folded:
            tr.emit("compact", f"method=summarize step={step} folded={folded} turns")
            tr.emit("assemble", f"tokens={tokens}/{budget} step={step}")
            tr.emit("observe", f"summary: {ctx.summary}", actor="model")
            tr.emit("check", f"pins={kept_pins}/{len(pins)} obligations="
                    f"{kept_owed}/{len(owed)}" + (" (from state)" if pinned else
                                                   " (from the summary)"))
    if not folded:
        tr.emit("assemble", f"tokens={tokens}/{budget} step={steps}")
    move, _ = llm.ask_json(DECIDE_SYSTEM, text, stub_decide, max_output_tokens=80)
    move = move or {"action": "escalate", "order_id": ""}
    tr.emit("decide", f"next={move.get('action')} order={move.get('order_id') or '?'}",
            actor="model")
    return {"world": world, "book": book, "ctx": ctx, "text": text, "log": log,
            "move": move, "trace": tr, "session": session, "store": store}


def act_on(r):
    """Whatever the model chose, a refund goes through the Chapter 6 ledger, same op."""
    if r["move"].get("action") in ("issue_refund", "reconcile"):
        row = r["book"].execute(OP, ARGS, pay(r["world"]), find(r["world"]))
        r["trace"].emit("ledger", f"{OP} -> {row['state']} (reconciled by key, "
                        "not paid again)")


if __name__ == "__main__":
    for pinned in (False, True):
        r = run(pinned)
        act_on(r)
        print(f"world: payments for #2001={len(r['world'].payments)} "
              f"ledger={r['book'].row(OP)['state']}")

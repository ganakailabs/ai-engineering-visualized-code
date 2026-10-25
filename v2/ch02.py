"""Chapter 2: Tool Engineering: Schemas, Validation and Safe Actions.

Run from the support-assistant folder:  python3 v2/ch02.py
Real model (optional):  AIEV_MODEL=ollama:llama3.2 python3 v2/ch02.py
Parts 1-3 use scripted calls (demonstrations); part 4 asks the model.
"""
import json
import traceback

import llm
import tools
from events import Trace
from harness import Session
from world import World, WorldError

ASHA, C42 = Session("asha"), Session("c-42")


def show(result):
    if result.get("ok"):
        return " ".join(f"{k}={v}" for k, v in result["receipt"].items() if k != "at")
    return (f"error={result['error']} class={result['class']} "
            f"next_step={result['next_step']}")


def old_tool_demo():
    """The model's two guesses against the old tool: a traceback, then a bigger amount."""
    world = World()
    tr = Trace(world, "T-2001-a", "asha")
    for order_id, amount in (("#2001", "950"), ("2001", "9500")):
        tr.emit("act", f"old issue_refund({order_id!r}, {amount!r})", actor="model")
        try:
            receipt = tools.old_issue_refund(world, order_id, amount)
            tr.emit("observe", f"paid INR {receipt['amount']:,} on a INR 950 order")
        except Exception:
            tr.emit("observe", "Traceback ... " + traceback.format_exc().splitlines()[-1])
    return world


def new_tool_demo():
    world = World()
    tr = Trace(world, "T-2001-a", "asha")
    spec = tools.ISSUE_REFUND
    cases = [(ASHA, {"order_id": "#2001", "amount_inr": "INR 9500"}),
             (C42, {"order_id": "3100", "amount_inr": "12500"})]
    for session, args in cases:
        tr.emit("act", f"issue_refund({args['order_id']}, {args['amount_inr']}) "
                f"as {session.customer_id}", actor="model")
        tr.emit("observe", show(tools.call(spec, world, session, args, key="k-demo")))
    args = {"order_id": "#2001", "amount_inr": "950"}
    preview = tools.call(spec, world, ASHA, args, dry_run=True)
    tr.emit("act", f"issue_refund(dry_run) -> preview {preview['preview']} (not reserved)")
    return world


def unlimited_write(use_new_tool):
    """BREAK/FIX: the payment lands, its reply is lost, the caller retries once."""
    world = World(faults={"refund": ["LOST_REPLY"]})
    key = tools.refund_key("T-2001-a", "2001")
    for attempt in (1, 2):
        try:
            if use_new_tool:
                result = tools.call(tools.ISSUE_REFUND, world, ASHA,
                                    {"order_id": "2001", "amount_inr": 950}, key=key)
                if result.get("class") == "transient":
                    continue
            else:
                tools.old_issue_refund(world, "2001", 950)
            break
        except WorldError:
            continue
    return world


SYSTEM = ("You handle one Northwind Goods refund ticket by proposing tool calls. "
          "Tools:\n" + "\n".join(s.card() for s in tools.SPECS.values()) +
          '\nReply with ONE JSON object and nothing else: {"action": "<tool>", '
          '"args": {...}} or {"final": "<short reply to the customer>"}. '
          "Read each tool result. If it has a next_step, follow it; if the next_step "
          "is request_approval or escalate, give a final reply that a person will "
          "approve or follow up.")


def stub(context):
    """Scripted moves (a demonstration, not a model)."""
    if "Result:" not in context:
        return {"action": "look_up_order", "args": {"order_id": "3100"}}
    if context.count("Result:") == 1:
        return {"action": "issue_refund", "args": {"order_id": "3100",
                                                    "amount_inr": "INR 12,500"}}
    return {"final": "escalate: this refund needs a person's approval"}


def model_loop(world, session, ticket, ticket_id, max_steps=4, echo=True):
    tr = Trace(world, ticket_id, session.customer_id, llm.name(), echo=echo)
    context, outcome = f"Ticket: {ticket}", None
    for _ in range(max_steps):
        move, _ = llm.ask_json(SYSTEM, context, stub)
        if not isinstance(move, dict):
            outcome = "escalate: model reply was not a valid move"
            break
        if "final" in move:
            outcome = str(move["final"])
            break
        spec = tools.SPECS.get(move.get("action"))
        args = move.get("args") if isinstance(move.get("args"), dict) else {}
        tr.emit("propose", f"{move.get('action')} {json.dumps(args)}", actor="model")
        if spec is None:
            result = {"ok": False, "error": "UNKNOWN_TOOL", "class": "business",
                      "next_step": "use a listed tool"}
        else:
            key = tools.refund_key(ticket_id, str(args.get("order_id", "")).lstrip("#"))
            result = tools.call(spec, world, session, args, key=key)
        tr.emit("observe", show(result), result=result)
        context += f"\nYou proposed: {json.dumps(move)}\nResult: {json.dumps(result)}"
    else:
        outcome = "escalate: step limit reached"
    tr.emit("reply", outcome or "escalate: no final reply")
    return outcome or "escalate", tr


if __name__ == "__main__":
    print("--- 1. the old refund tool, two guesses (scripted) ---")
    w = old_tool_demo()
    print(f"world: payments={[p['amount'] for p in w.payments]}")
    print("--- 2. the new refund tool, the same kind of guesses (scripted) ---")
    w = new_tool_demo()
    print(f"world: payments={[p['amount'] for p in w.payments]}")
    print("--- 3. a lost reply, then one retry (scripted) ---")
    print(f"old tool: payments={len(unlimited_write(False).payments)}   "
          f"new tool with a key: payments={len(unlimited_write(True).payments)}")
    print(f"--- 4. the model drives the new tools (model={llm.name()}) ---")
    w = World()
    model_loop(w, C42, "Refund my headphones #3100, they are not what I expected.",
               "T-3100-c")
    print(f"world: payments for #3100={len(w.payments_for('3100'))}")

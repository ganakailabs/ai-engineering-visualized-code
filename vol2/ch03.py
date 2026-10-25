"""Chapter 3: Planning: Dependencies, Validation and Replanning.

Run from the repo root:  python3 vol2/ch03.py
Real model (optional):  AIEV_MODEL=ollama:llama3.2 python3 vol2/ch03.py
The stub plans are a script (a demonstration); a real model's plan will differ,
and check_plan() decides whether it may run at all.
"""
import json

import llm
import planner
from events import Trace
from world import World

TICKET = ("T-2001-s", "My ceramic mug set #2001 arrived cracked. Please swap it for "
          "the blue set, or the green one if blue is gone.")

SYSTEM = ("Break one Northwind Goods ticket into steps. Step tools and their args: "
          "verify_order(order_id), check_stock(item), choose(item), "
          "send_label(order_id, item), book_pickup(order_id, item), "
          "partner_dropoff(order_id, item), reply(text). Items are exactly "
          "'mug set blue' or 'mug set green'. Each step has an id, a tool, args, and "
          "'after': the ids that must finish first. End with one reply step that waits "
          'for every other step. Reply with ONE JSON object and nothing else: {"steps": '
          '[{"id": "n1", "tool": "verify_order", "args": {"order_id": "2001"}, '
          '"after": []}, ...]}')


def first_plan(chosen="mug set blue"):
    return {"steps": [
        {"id": "n1", "tool": "verify_order", "args": {"order_id": "2001"}, "after": []},
        {"id": "n2", "tool": "check_stock", "args": {"item": chosen}, "after": ["n1"]},
        {"id": "n3", "tool": "choose", "args": {"item": chosen}, "after": ["n2"]},
        {"id": "n4", "tool": "send_label", "args": {"order_id": "2001", "item": chosen},
         "after": ["n1", "n3"]},
        {"id": "n5", "tool": "book_pickup", "args": {"order_id": "2001", "item": chosen},
         "after": ["n4"]},
        {"id": "n6", "tool": "reply", "args": {"text": "Swap booked."}, "after": ["n5"]}]}


def stub(user):
    """Scripted plans (a demonstration, not a model)."""
    if "Surprise:" not in user:
        return first_plan()
    if "whole plan again" in user:        # BREAK: a full replan, every step again
        return first_plan("mug set green" if "OUT_OF_STOCK" in user else "mug set blue")
    if "OUT_OF_STOCK" in user:            # new branch from CHECK STOCK on, for green
        green = first_plan("mug set green")["steps"][1:]
        for s in green:
            s["id"] += "b"
            s["after"] = [d if d == "n1" else d + "b" for d in s["after"]]
        return {"steps": green}
    return {"steps": [                    # the courier is down: a partner store instead
        {"id": "n5b", "tool": "partner_dropoff",
         "args": {"order_id": "2001", "item": "mug set blue"}, "after": ["n4"]},
        {"id": "n6", "tool": "reply", "args": {"text": "Drop it at a partner store."},
         "after": ["n5b"]}]}


def ask(user):
    plan, _ = llm.ask_json(SYSTEM, user, stub, max_output_tokens=900)
    return plan


def handle(world, ticket=TICKET, naive=False, echo=True, max_repairs=2,
           fresh_keys=True):
    """Plan, check, run; on a surprise repair only the broken branch (or, naive=True,
    throw the plan away and rerun everything with fresh keys: the BREAK)."""
    ticket_id, text = ticket
    tr = Trace(world, ticket_id, "asha", llm.name(), echo=echo)
    plan = ask(f"Ticket: {text}")
    problems = planner.check_plan(plan)
    if problems:
        tr.emit("check", f"plan invalid: {problems[0]}", problems=problems)
        tr.emit("escalate", "a person will plan this ticket")
        return {"status": "escalated", "trace": tr, "plan": plan}
    planner.show_tree(plan["steps"], tr.emit)
    tr.emit("check", "plan valid")
    receipts, attempt = {}, 0
    for attempt in range(max_repairs + 1):
        key_fn = ((lambda t, s, n=attempt: f"{planner.node_key(t, s)}-try{n}")
                  if naive and fresh_keys else planner.node_key)
        result = planner.execute(plan, world, ticket_id, tr.emit, receipts, key_fn)
        if result["status"] == "done":
            tr.emit("reply", "done: " + receipts[[s for s in plan["steps"]
                                                  if s["tool"] == "reply"][0]["id"]]
                    ["receipt"]["sent"])
            return {"status": "done", "trace": tr, "plan": plan, "receipts": receipts}
        if attempt == max_repairs:
            break
        failed, code = result["step"], result["code"]
        user = (f"Ticket: {text}\nSurprise: {failed['id']} {failed['tool']} failed "
                f"with {code}.\n")
        if naive:                                       # BREAK: full replan
            tr.emit("plan", "replan everything from scratch")
            new = ask(user + "Write the whole plan again.")
            receipts = {}
        else:                                           # FIX: repair the branch
            scope = planner.repair_scope(plan, receipts, failed, code)
            tr.emit("plan", f"repair branch={scope['branch']} kept=["
                    + ", ".join(planner.BRANCH[s["tool"]] for s in scope["kept"])
                    + "] invalidated=["
                    + ", ".join(planner.BRANCH[s["tool"]] for s in scope["undo"]) + "]",
                    kept=[s["id"] for s in scope["kept"]],
                    invalid=sorted(scope["invalid"]))
            for s in scope["undo"]:                     # compensate, with its own key
                label = receipts.pop(s["id"])["receipt"]["receipt_id"]
                world.void_label(label, key=f"k-{ticket_id}-void-{label}")
                tr.emit("act", f"void_label {label} (compensation)")
            for sid in scope["invalid"]:
                receipts.pop(sid, None)
            kept = scope["kept"]
            new = ask(user + "Finished steps that still count (reuse their ids in "
                      "'after'): " + json.dumps(kept) + "\nGive only the new steps.")
            if isinstance(new, dict) and isinstance(new.get("steps"), list):
                new = {"steps": [dict(s) for s in kept] + new["steps"]}
        problems = planner.check_plan(new)
        if problems:
            tr.emit("check", f"new plan invalid: {problems[0]}", problems=problems)
            break
        tr.emit("check", "new plan valid")
        plan = new
    tr.emit("escalate", "a person will finish this ticket")
    return {"status": "escalated", "trace": tr, "plan": plan, "receipts": receipts}


def swap_world(faults=None):
    """One blue set left when the ticket starts; the scripted fault sells it."""
    return World(stock={"mug set blue": 1, "mug set green": 4},
                 faults=faults or {"book_pickup": ["SELL_OUT"]})


if __name__ == "__main__":
    print(f"--- repair only the broken branch (model={llm.name()}) ---")
    w = swap_world()
    handle(w)
    print(f"world: live labels={[lab['item'] for lab in w.live_labels('2001')]} "
          f"send_label calls={len(w.write_calls('send_label'))}")
    print("--- BREAK: replan everything, fresh keys ---")
    w = swap_world()
    handle(w, naive=True)
    print(f"world: live labels={[lab['item'] for lab in w.live_labels('2001')]} "
          f"send_label calls={len(w.write_calls('send_label'))}")

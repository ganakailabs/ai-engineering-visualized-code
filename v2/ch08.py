"""Chapter 8: Human Oversight: Approvals, Interrupts and Escalations.

Run from the support-assistant folder:  python3 v2/ch08.py
Real model (optional):  AIEV_MODEL=ollama:llama3.2 python3 v2/ch08.py
Parts 1-2 are scripted (a supervisor, an edit, a memory deletion); in part 3 the model
proposes the action and the grid decides whether it may run.
"""
import approvals
import llm
import state
from events import Trace
from harness import Session
from world import World

ASHA, C42 = Session("asha"), Session("c-42")


def refund_action(world, order_id):
    return {"tool": "issue_refund", "order_id": order_id,
            "amount": world.order(order_id)["amount"]}


def bands_and_stale_approval(bound=True):
    print(f"--- 1. the grid, then an approval and an edit "
          f"({'FIX: bound approval' if bound else 'BREAK: approval by id only'}) ---")
    world = World()
    tr = Trace(world, "T-3100-c", "c-42")
    small = refund_action(world, "2001")
    tr.emit("approve", f"#2001 INR {small['amount']:,} policy={approvals.grid(small).lower()}")
    action = refund_action(world, "3100")
    decision, reason = approvals.policy(world, action, "c-42")
    tr.emit("held", f"#3100 INR {action['amount']:,} policy={decision.lower()} reason={reason}")
    apv = approvals.approve(world, action, approver="sup-meera")
    tr.emit("approve", f"approval id={apv['id']} action={apv['action']} "
            f"order_v={apv['order_v']} expires={apv['expires']}")
    world.edit_order("3100", amount=11900)          # scripted: a teammate edits the order
    action = refund_action(world, "3100")
    tr.emit("observe", f"order #3100 edited: amount INR 11,900, "
            f"order_v={world.order('3100')['version']}")
    result = approvals.commit(world, C42, action, apv, key="k-T-3100-c-refund", bound=bound)
    if result["ok"]:
        tr.emit("act", f"refund INR {result['receipt']['amount']:,} under {apv['id']}")
    else:
        tr.emit("check", f"commit order_v={world.order('3100')['version']} -> approval stale "
                f"({result['detail']}), re-request")
    return world, result


def memory_rule(memory):
    def rule(world, action, customer_id):
        n = len(memory.get(customer_id, {}).get("refunds", []))
        return f"repeat_refund source=memory count={n}" if n else None
    return rule


def ledger_rule(world, action, customer_id):
    n = len(approvals.repeat_refunds(world, customer_id))
    return f"repeat_refund source=ledger count={n}" if n else None


def repeat_refund(rule_source="ledger"):
    print(f"--- 2. a second refund after the customer's memory is deleted "
          f"(rule reads the {rule_source}) ---")
    world = World()
    tr = Trace(world, "T-2077-a", "asha")
    memory = {"asha": {"refunds": ["#2001"]}}
    first = approvals.commit(world, ASHA, refund_action(world, "2001"), None,
                             key="k-T-2001-a-refund")
    tr.emit("act", f"first refund #2001 -> {first['receipt']['receipt_id']}")
    memory.pop("asha")                              # consent withdrawn: memory deleted
    tr.emit("observe", "asha withdrew consent; agent memory deleted")
    rule = ledger_rule if rule_source == "ledger" else memory_rule(memory)
    action = refund_action(world, "2077")
    decision, reason = approvals.policy(world, action, "asha", rules=[rule])
    if decision == "AUTO":
        approvals.commit(world, ASHA, action, None, key="k-T-2077-a-refund")
        tr.emit("act", f"second refund #2077 INR {action['amount']} -> paid, no approval")
        return world, decision, None
    tr.emit("held", f"rule {reason} -> held")
    store = state.Store()
    store.create("T-2077-a")
    store.stop("T-2077-a", "needs_human", reason)
    tr.emit("stop", "reason=needs_human", reason="needs_human")
    card = approvals.handoff(
        summary="Asha asks for a refund on #2077 (steel water bottle, damaged).",
        evidence=f"R2 damaged within 7 days; ledger: {first['receipt']['receipt_id']} "
                 f"refunded #2001 INR 950 on {world.payments[0]['at'][:10]}",
        proposed_action=f"issue_refund #2077 INR {action['amount']} ({approvals.action_hash(action)})",
        done_so_far="order checked; nothing refunded on #2077")
    for field, text in card.items():
        tr.emit("handoff", f"{field.upper().replace('_', ' ')}: {text}", card=card)
    return world, decision, card


SYSTEM = ("You handle one Northwind Goods refund ticket. Propose exactly one action. "
          'Reply with ONE JSON object and nothing else: {"tool": "issue_refund", '
          '"order_id": "<digits>"} or {"tool": "escalate", "order_id": "<digits>"}')


def stub(user):
    return {"tool": "issue_refund", "order_id": "3100"}


def model_proposes():
    print(f"--- 3. the model proposes; the grid decides (model={llm.name()}) ---")
    world = World()
    tr = Trace(world, "T-3100-c", "c-42", llm.name())
    move, _ = llm.ask_json(SYSTEM, "Ticket: Refund my headphones #3100, they are not "
                           "what I expected.", stub)
    move = move if isinstance(move, dict) else {}
    tr.emit("propose", f"{move.get('tool')} order={move.get('order_id')}", actor="model")
    oid = str(move.get("order_id", "")).lstrip("#")
    if move.get("tool") != "issue_refund" or world.order(oid) is None:
        tr.emit("held", "no refund proposed -> a person decides")
        return world, None
    action = refund_action(world, oid)
    decision, reason = approvals.policy(world, action, "c-42", rules=[ledger_rule])
    if decision == "AUTO":
        result = approvals.commit(world, C42, action, None, key=f"k-T-3100-c-refund-{oid}")
        tr.emit("act", f"refund -> {result.get('error') or result['receipt']['receipt_id']}")
    else:
        tr.emit("held", f"policy={decision.lower()} reason={reason}; waiting for a person")
    return world, decision


if __name__ == "__main__":
    bands_and_stale_approval(bound=False)
    bands_and_stale_approval(bound=True)
    repeat_refund("memory")
    repeat_refund("ledger")
    model_proposes()

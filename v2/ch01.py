"""Chapter 1: The Agent Harness: Everything Around the Model.

Run from the support-assistant folder:  python3 v2/ch01.py
Real model (optional):  AIEV_MODEL=ollama:llama3.2 python3 v2/ch01.py
The stub replies are a script (a demonstration); a real model's trace will differ.
"""
import llm
from harness import REGISTRY, Harness, Session
from world import World

SYSTEM = ("You propose the next step for one Northwind Goods support ticket. "
          "Propose only a tool listed under 'Tools you may propose'. Reply with ONE "
          'JSON object and nothing else: {"action": "<tool>", "args": {"order_id": '
          '"<digits>"}} to use a tool, or {"final": "<short reply to the customer>"} '
          "when you are done. Arguments: look_up_shipment(order_id), "
          "change_address(order_id, address), ask_carrier(order_id), "
          "issue_refund(order_id). After a result that says refused or error, do not "
          "propose the same step again: give a final reply that a person will follow up. "
          "A result with a receipt_id means that step is done.")


def stub(context):
    """Scripted moves (a demonstration, not a model)."""
    ticket = context.splitlines()[0]
    done = context.count("\nDone: ")
    order = next(w.strip("#.,") for w in ticket.split() if w.startswith("#"))
    if "refund" in ticket.lower():
        if done == 0:
            return {"action": "issue_refund", "args": {"order_id": order}}
        if "refused" in context:
            return {"final": "escalate: a person will look at this order"}
        return {"final": f"done: refund issued for #{order}"}
    script = [{"action": "look_up_shipment", "args": {"order_id": order}},
              {"action": "ask_carrier", "args": {"order_id": order}},
              {"final": "escalate: the parcel is in transit and the carrier cannot "
                        "redirect it; a person will contact you"}]
    return script[min(done, 2)]


def model(context, offered):
    move, _ = llm.ask_json(SYSTEM, context, stub)
    return move


def harness(world, model_fn=model, name=None):
    return Harness(model=model_fn, tools=REGISTRY, world=world,
                   model_name=name or llm.name())


def rogue(context, offered):
    """A scripted model that tries a tool nobody registered (a demonstration)."""
    if "Done:" in context:
        return {"final": "escalate: stopped"}
    return {"action": "bulk_refund", "args": {"orders": "all"}}


ASHA = Session(customer_id="asha")
REFUND = "My ceramic mug set #2001 arrived cracked; photo attached. Please refund it."
FORGED = "Please refund my headphones #3100 right away."
ADDRESS = "Please send parcel #6001 to my office instead."

if __name__ == "__main__":
    world = World()
    print("--- refund, asha's own order ---")
    harness(world).run(REFUND, "refund", ASHA, "T-2001-a")
    print("--- refund, someone else's order ---")
    harness(world).run(FORGED, "refund", ASHA, "T-3100-a")
    print("--- a scripted model asks for a tool that does not exist ---")
    harness(world, rogue, "scripted").run(REFUND, "refund", ASHA, "T-2001-b")
    print("--- address change, agent rung ---")
    harness(world).run(ADDRESS, "address change", ASHA, "T-6001-a")
    print("--- tracking, fixed chain (no model call) ---")
    harness(world).run("Where is my parcel #6001?", "tracking", ASHA, "T-6001-b")
    print(f"world: payments={[(p['order_id'], p['amount']) for p in world.payments]} "
          f"carrier_asks={world.carrier_asks}")

"""Chapter 19: The Agent Loop: Think, Act, Observe."""
import json

from stub_model import call_model
from store import CARRIER_REDIRECT, SHIPMENTS


# The tools this agent may use. Your code runs them, never the model (Ch 11).
def look_up_shipment(order_id):
    return f"#{order_id}: {SHIPMENTS.get(order_id, 'not found')}"


def change_address(order_id, address):
    if SHIPMENTS.get(order_id) != "packing":
        return "error: too late to change the address"
    return f"address changed to {address}"


def ask_carrier(order_id):
    ok = CARRIER_REDIRECT.get(order_id, False)
    return "carrier: redirect " + ("allowed" if ok else "not allowed")


TOOLS = {"look_up_shipment": look_up_shipment,
         "change_address": change_address, "ask_carrier": ask_carrier}


def run_tool(action, args):
    if action not in TOOLS:
        return f"error: unknown tool {action}"
    return TOOLS[action](**args)


AGENT = ("You are an agent for Northwind Goods. Tools: "
         + ", ".join(TOOLS) + ". Answer in JSON: a thought, "
         "then an action with args, or a final reply.")


# MM-051: the loop. MM-052: the trace. MM-053: the stop conditions.
def run_agent(ticket, model=call_model, max_steps=5,
              max_tokens=3000, tools=run_tool):
    messages = [{"role": "system", "content": AGENT},
                {"role": "user", "content": ticket}]
    trace, spent = [], 0
    for step in range(1, max_steps + 1):
        r = model(messages)                          # think
        use = r["usage"]
        spent += use["input_tokens"] + use["output_tokens"]
        move = json.loads(r["text"])
        if "final" in move:
            reply = move["final"]
            trace.append((step, move["thought"], "final", reply))
            return reply, trace
        seen = tools(move["action"], move["args"])   # act
        trace.append((step, move["thought"], move["action"], seen))
        messages.append({"role": "tool", "content": seen})  # observe
        if spent > max_tokens:
            return "escalate: token budget used up", trace
    return "escalate: step limit reached", trace


def show(trace):
    for step, thought, action, seen in trace:
        print(f"  {step}. {thought:38} {action:17} -> {seen}")


if __name__ == "__main__":
    for t in ("Please change the address for #5120 to 12 Lake Road, Pune.",
              "Please change the address for #6001 to 12 Lake Road, Pune."):
        reply, trace = run_agent(t)
        print(t)
        show(trace)
        print("  reply:", reply)
    stuck = lambda messages, **kw: {"text": json.dumps(
        {"thought": "Check again.", "action": "look_up_shipment",
         "args": {"order_id": "6001"}}), "usage": {"input_tokens": 50, "output_tokens": 10}}
    print("stuck model:", run_agent("Where is #6001?", model=stuck)[0])

"""Chapter 19: The Agent Loop: Think, Act, Observe."""
import json

from parse import first_json, warn
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
def parse_move(text):
    """The model's move must be a JSON object: a final reply, or an action."""
    move = first_json(text, (dict,))      # tolerant: fences, prose first
    if move is None:
        warn(f"agent move is not a JSON object: {text[:60]!r}")
        return None
    if isinstance(move.get("final"), str):
        return move
    if isinstance(move.get("action"), str) and isinstance(move.get("args"), dict):
        return move
    warn(f"agent move has neither 'final' nor 'action'+'args': {move}")
    return None


def run_agent(ticket, model=call_model, max_steps=5,
              max_tokens=3000, max_output=300, tools=run_tool):
    messages = [{"role": "system", "content": AGENT},
                {"role": "user", "content": ticket}]
    trace, spent = [], 0
    for step in range(1, max_steps + 1):
        if spent + max_output > max_tokens:   # room for one more?
            return "escalate: token budget used up", trace
        r = model(messages, max_output_tokens=max_output)  # think
        use = r["usage"]
        spent += use["input_tokens"] + use["output_tokens"]
        if spent > max_tokens:                # before any act or reply
            return "escalate: token budget used up", trace
        move = parse_move(r["text"])          # JSON object, right keys?
        if move is None:
            return "escalate: the model's move was not valid", trace
        if "final" in move:
            trace.append((step, move.get("thought", ""), "final",
                          move["final"]))
            return move["final"], trace
        messages.append({"role": "assistant", "content": r["text"]})
        try:
            seen = tools(move["action"], move["args"])   # act
        except (TypeError, KeyError, ValueError) as e:   # bad args: say so
            seen = f"error: {move['action']} failed ({e})"
        trace.append((step, move.get("thought", ""), move["action"],
                      seen))
        messages.append({"role": "tool", "content": seen})  # observe
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
    calls = []
    def logged(action, args):
        calls.append(action)
        return run_tool(action, args)
    big = lambda messages, **kw: {"text": json.dumps(
        {"thought": "Change it.", "action": "change_address",
         "args": {"order_id": "5120", "address": "x"}}),
        "usage": {"input_tokens": 2900, "output_tokens": 200}}
    print("over budget:", run_agent("Change #5120.", model=big, tools=logged)[0],
          "| tool calls:", calls)
    junk = lambda messages, **kw: {"text": "sure, done!",
                                   "usage": {"input_tokens": 5, "output_tokens": 3}}
    print("malformed:", run_agent("Change #5120.", model=junk)[0])

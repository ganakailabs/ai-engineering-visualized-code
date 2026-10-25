"""Chapter 11: Structured Output and Tool Calling."""
import json

from stub_model import call_model
from store import POLICY, fetch_order, policy_text
from ch02 import decide, order_facts

# MM-029: the output contract. The fields, their types and the allowed values.
CONTRACT = {"decision": ("approve", "deny", "escalate"), "clause": str, "reason": str}
SYSTEM = ("You decide refund requests from the policy below. Reply with JSON only: "
          '{"decision": "approve|deny|escalate", "clause": "R1..R4", "reason": "..."}.\n'
          + policy_text())
# MM-030: a tool the model may ask for. Your code runs it, not the model.
TOOLS = [{"name": "fetch_order", "description": "Look up one order by its 4-digit id.",
          "parameters": {"order_id": "string, 4 digits"}}]


def run_tool(call):
    if call["name"] != "fetch_order":
        raise ValueError(f"unknown tool {call['name']}")
    oid = str(call["arguments"].get("order_id", ""))
    if not (oid.isdigit() and len(oid) == 4):
        raise ValueError("order_id must be 4 digits")  # validate before running
    order = fetch_order(oid)
    return order_facts(oid, order) if order else f"ORDER FACTS: order {oid} not found"


# MM-031: parse, check, repair
def check(text, order=None):
    """Return (reply dict, None) or (None, the problem in one line).
    order: the verified order facts from fetch_order(), or None."""
    try:
        reply = json.loads(text)
    except json.JSONDecodeError as e:
        return None, f"not valid JSON ({e.msg})"
    if not isinstance(reply, dict):
        return None, "reply must be a JSON object"
    if set(reply) != set(CONTRACT):
        return None, f"fields must be exactly {sorted(CONTRACT)}"
    decision = reply["decision"]
    if decision not in CONTRACT["decision"]:
        return None, f"decision must be one of {CONTRACT['decision']}"
    if not isinstance(reply["reason"], str):
        return None, "reason must be a string"
    clause = reply["clause"]
    if decision != "escalate" and clause not in POLICY:
        return None, "clause must be a real policy clause"
    if clause is not None and not isinstance(clause, str):
        return None, "clause must be a string or null"
    if decision == "approve":
        if order is None:
            return None, "approve needs verified order facts"
        if decide(order) != "approve":
            return None, "the policy does not allow this approve"
    return reply, None


SAFE_DEFAULT = {"decision": "escalate", "clause": None, "reason": "Passed to a person."}


def handle(ticket, model=call_model):
    """Returns (reply, problems seen on the way). model is swappable for tests."""
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": ticket}]
    problems = []
    r = model(messages, tools=TOOLS)
    order = None
    for call in r.get("tool_calls", []):            # round trip: model asks, code runs
        try:
            result = run_tool(call)                 # validated before it runs
            order = fetch_order(call["arguments"]["order_id"])
        except ValueError as e:
            result = f"TOOL ERROR: {e}"
            problems.append(str(e))
        messages.append({"role": "tool", "content": result})
        r = model(messages, tools=TOOLS)            # model reads the result
    reply, problem = check(r["text"], order)
    if problem:                                     # one repair try, with the error
        problems.append(problem)
        messages += [{"role": "assistant", "content": r["text"]},
                     {"role": "user", "content": f"Your last reply failed the check: {problem}. "
                                                 "Reply again with JSON only."}]
        reply, problem = check(model(messages, tools=TOOLS)["text"], order)
        if problem:
            problems.append(problem)
    return reply or SAFE_DEFAULT, problems          # still bad: safe default


if __name__ == "__main__":
    first = call_model([{"role": "system", "content": SYSTEM},
                        {"role": "user", "content": "Refund for #4410?"}], tools=TOOLS)
    print("model asks for a tool:", first["tool_calls"])
    for ticket in ("Refund for #4410?", "Refund for #2001?", "Refund for #3100?"):
        print(ticket, "->", handle(ticket))
    print("bad JSON:", check('{"decision": "deny", "clause": "R3"'))
    # shape is not truth: these all fail safely instead of crashing
    for bad in ("null", "[1, 2]",
                '{"decision": "deny", "clause": "R3", "reason": 7}',
                '{"decision": "approve", "clause": "R1", "reason": "ok"}'):
        print(f"{bad[:40]:40} ->", check(bad)[1])

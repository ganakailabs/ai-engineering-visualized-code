"""Exact output formats for REAL models (used by ollama_model.py).

The stub is scripted and ignores these. A real model only follows a format it
is shown, so before each call the adapter adds the matching instruction, with
a tiny example, and asks Ollama for JSON mode where JSON is expected.
Provider-neutral: the same text works for any chat model.
"""

DECISION = ("OUTPUT FORMAT: reply on ONE line, starting with exactly one label "
            "and a colon: approve: <reason with clause id> | deny: <reason "
            "with clause id> | escalate: <what is missing>. No brackets, no "
            "other text. Example: deny: <reason> (R3)")
ANSWER = ("OUTPUT FORMAT: reply on ONE line: answer: <answer> [passage id], "
          "or escalate: <what is missing>. Example: answer: <text> [S1]")
ROUTER = ("OUTPUT FORMAT: reply with exactly one lowercase word from: refund, "
          "tracking, warranty, other. Example: refund")
# Real models guess argument names (new_address, refund) unless shown them.
# These are the book's toy tools (Ch 19, 20, 22), named exactly as the code has them.
TOOL_ARGS = ("Use ONLY these exact tool names and argument names: "
             "look_up_shipment(order_id), change_address(order_id, address), "
             "ask_carrier(order_id), issue_refund(order_id, amount as a whole "
             "number of INR), check_stock(item), reserve(item), "
             "send_label(order_id), ask_customer(question).")
AGENT = ("OUTPUT FORMAT: reply with ONE JSON object, nothing else. To use a "
         'tool: {"thought": "<why>", "action": "<tool name>", "args": '
         '{"order_id": "5120"}}. To finish: {"thought": "<why>", "final": '
         '"done: <reply>"} or {"thought": "<why>", "final": "escalate: '
         '<reason>"}.')
PLAN = ("OUTPUT FORMAT: reply with ONE JSON object, nothing else: "
        '{"steps": [{"tool": "check_stock", "args": {"item": "mug set '
        'green"}}, {"tool": "send_label", "args": {"order_id": "2001"}}]}')
JSON_DECISION = ("OUTPUT FORMAT: reply with ONE JSON object, nothing else. "
                 'Example: {"decision": "deny", "clause": "R3", "reason": '
                 '"<reason>"}')


def for_messages(messages):
    """(instruction or None, wants_json) for this call, from the system text."""
    system = " ".join(str(m["content"]) for m in messages
                      if m["role"] == "system").lower()
    if "you are an agent" in system:
        return AGENT + " " + TOOL_ARGS, True
    if "write a plan" in system:
        return PLAN + " " + TOOL_ARGS, True
    if "reply with json" in system:
        return JSON_DECISION, True
    if "classify the ticket" in system:
        return ROUTER, False
    if "passages:" in system:
        return ANSWER, False
    if "policy (version" in system or "approve|deny|escalate" in system:
        return DECISION, False
    return None, False

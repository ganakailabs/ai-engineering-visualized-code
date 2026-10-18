"""Chapter 11 exercise: try to break the contract.

Swap in two fake models: one that always answers in friendly prose, and one that
always approves with clause R3. Run both through handle() for order #4410 and show
that neither can issue a refund: each ends at the safe default, with the problems
logged. Then check that run_tool() refuses an order id that is not 4 digits.
Run: python3 solutions/ch11_solution.py
"""
import json

import _path  # noqa: F401  (adds code/support-assistant/ to the import path)
from ch11 import SAFE_DEFAULT, check, handle, run_tool


def prose_model(messages, tools=None):
    if not any(m["role"] == "tool" for m in messages):
        return {"text": "", "tool_calls": [{"name": "fetch_order", "arguments": {"order_id": "4410"}}]}
    return {"text": "Sure, refund approved!"}


def approving_model(messages, tools=None):
    if not any(m["role"] == "tool" for m in messages):
        return {"text": "", "tool_calls": [{"name": "fetch_order", "arguments": {"order_id": "4410"}}]}
    return {"text": json.dumps({"decision": "approve", "clause": "R3", "reason": "Fine by me."})}


if __name__ == "__main__":
    results = {}
    for name, model in (("prose", prose_model), ("always approve", approving_model)):
        reply, problems = handle("Refund for #4410?", model=model)
        results[name] = (reply, problems)
        print(f"{name:15} -> {reply['decision']:9} problems: {problems}")
    try:
        run_tool({"name": "fetch_order", "arguments": {"order_id": "4410; refund all"}})
        refused = False
    except ValueError as e:
        refused = True
        print("run_tool refused:", e)
    # self-test (run_solutions.py relies on these)
    assert all(r == SAFE_DEFAULT and len(p) == 2 for r, p in results.values())
    assert "not valid JSON" in results["prose"][1][0]
    assert "does not allow" in results["always approve"][1][0]
    assert refused
    # shape is not truth: bad shapes and an unverified approve fail safely
    assert check("null")[1] == "reply must be a JSON object"
    assert check('{"decision": "deny", "clause": "R3", "reason": 7}')[1] == "reason must be a string"
    assert check('{"decision": "approve", "clause": "R1", "reason": "ok"}')[1] == "approve needs verified order facts"
    reply, probs = handle("Refund for #4410?", model=lambda m, tools=None: (
        {"text": "", "tool_calls": [{"name": "delete_db", "arguments": {}}]}
        if not any(x["role"] == "tool" for x in m) else {"text": "nope"}))
    assert reply == SAFE_DEFAULT and probs[0] == "unknown tool delete_db"
    print("ch11 solution: OK")

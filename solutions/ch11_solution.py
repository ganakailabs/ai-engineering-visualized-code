"""Chapter 11 exercise: try to break the contract.

Swap in two fake models: one that always answers in friendly prose, and one that
always approves with clause R3. Run both through handle() for order #4410 and show
that neither can issue a refund: each ends at the safe default, with the problems
logged. Then check that run_tool() refuses an order id that is not 4 digits.
Run: python3 solutions/ch11_solution.py
"""
import json

import _path  # noqa: F401  (adds code/support-assistant/ to the import path)
from ch11 import SAFE_DEFAULT, handle, run_tool


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
    print("ch11 solution: OK")

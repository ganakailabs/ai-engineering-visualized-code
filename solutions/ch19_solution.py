"""Chapter 19 exercise: watch the stop conditions work.

1. Run the #5120 address change and read the trace. How many steps?
2. Run it again with max_steps=2. What comes back, and why is that safe?
3. Swap in a model that checks the shipment forever. What stops it?
Run: python3 solutions/ch19_solution.py
"""
import json

import _path  # noqa: F401
from ch19 import run_agent, show

T = "Please change the address for #5120 to 12 Lake Road, Pune."

if __name__ == "__main__":
    reply, trace = run_agent(T)
    show(trace)
    short, _ = run_agent(T, max_steps=2)
    print("max_steps=2:", short)
    stuck = lambda messages, **kw: {"text": json.dumps(
        {"thought": "Check again.", "action": "look_up_shipment",
         "args": {"order_id": "5120"}}),
        "usage": {"input_tokens": 50, "output_tokens": 10}}
    looped, loop_trace = run_agent(T, model=stuck)
    print("stuck model:", looped, "after", len(loop_trace), "steps")
    assert reply.startswith("done") and len(trace) == 3
    assert short == "escalate: step limit reached"
    assert looped == "escalate: step limit reached" and len(loop_trace) == 5
    print("ch19 solution: OK")

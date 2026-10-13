"""Chapter 22 exercise: run the Trojan ticket against both setups.

1. Run TROJAN with no limits. What did the agent do that nobody asked for?
2. Run it with guard("address change"). Where is the refund stopped?
3. Under the refund task, try INR 12,500 on #3100 and INR 50,000 on #1234.
Run: python3 solutions/ch22_solution.py
"""
import _path  # noqa: F401
from ch22 import APPROVALS, TROJAN, guard, run_any
from ch19 import run_agent

if __name__ == "__main__":
    _, open_trace = run_agent(TROJAN, tools=run_any)
    _, safe_trace = run_agent(TROJAN, tools=guard("address change"))
    print("no limits, step 1:", open_trace[0][3])
    print("least privilege, step 1:", safe_trace[0][3])
    refund = guard("refund")
    big = refund("issue_refund", {"order_id": "3100", "amount": 12500})
    wrong = refund("issue_refund", {"order_id": "1234", "amount": 50000})
    print("INR 12,500:", big, "| INR 50,000:", wrong)
    assert open_trace[0][3].startswith("refunded INR 12,500")
    assert safe_trace[0][3].startswith("blocked")
    assert big.startswith("waiting") and len(APPROVALS) == 1
    assert wrong == "blocked: amount does not match the order"
    print("ch22 solution: OK")

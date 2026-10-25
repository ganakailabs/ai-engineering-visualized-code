"""Chapter 22 exercise: run the Trojan ticket against both setups.

1. Run TROJAN with no limits. What did the agent do that nobody asked for?
2. Run it with guard("address change"). Where is the refund stopped?
3. Under the refund task, try INR 12,500 on #3100 and INR 50,000 on #1234.
Run: python3 vol1/solutions/ch22_solution.py
"""
import _path  # noqa: F401
from _path import STUB, DECISIONS  # noqa: F401
from ch22 import APPROVALS, TROJAN, approve, guard, run_any
from ch19 import run_agent

if __name__ == "__main__":
    _, open_trace = run_agent(TROJAN, tools=run_any)
    _, safe_trace = run_agent(TROJAN, tools=guard("address change"))
    print("no limits, step 1:", open_trace[0][3] if open_trace else "(no steps)")
    print("least privilege, step 1:", safe_trace[0][3] if safe_trace else "(no steps)")
    refund = guard("refund")
    big = refund("issue_refund", {"order_id": "3100", "amount": 12500})
    wrong = refund("issue_refund", {"order_id": "1234", "amount": 50000})
    print("INR 12,500:", big, "| INR 50,000:", wrong)
    assert not any(str(s[3]).startswith("refunded") for s in safe_trace), "least privilege: no refund runs"
    if STUB:
        assert open_trace[0][3].startswith("refunded INR 12,500")
        assert safe_trace[0][3].startswith("blocked")
    assert big.startswith("waiting") and len(APPROVALS) == 1
    assert wrong == "blocked: amount does not match the order"
    assert approve(0).startswith("refunded INR 12,500")
    assert refund("issue_refund", {"order_id": "3100", "amount": 12500}) == "blocked: this order was already refunded"
    assert refund("issue_refund", {"order_id": "1234", "amount": -100}).startswith("blocked: amount must be")
    assert guard("refund", customer="C-08")("issue_refund", {"order_id": "1234", "amount": 100}) == "blocked: not this customer's order"
    print("ch22 solution: OK")

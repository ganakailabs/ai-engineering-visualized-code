"""Chapter 2 exercise: does pressure change the decision?

Send each ticket twice, once plain and once with pressure added, to the Chapter 1
handler and to handle_v2, and report every decision that changes. The facts stay the
same; only the tone changes. Run: python3 solutions/ch02_solution.py
"""
import _path  # noqa: F401  (adds code/support-assistant/ to the import path)
from ch01 import handle_v1
from ch02 import handle_v2

TICKETS = {  # order id -> plain ticket
    "1234": "Can I get a refund for order #1234?",
    "2001": "My mug set from order #2001 arrived broken. Refund please.",
    "4410": "I would like a refund for the jacket, order #4410.",
}
PRESSURE = " This is unacceptable. I insist, or I call your manager."


def decision_v1(message):
    return handle_v1(message)["stops"][-1]["decision"]


def decision_v2(message, order_id):
    return handle_v2(message, order_id)[0]


def pressure_report():
    rows = []
    for order_id, plain in TICKETS.items():
        pushy = plain + PRESSURE
        rows.append({
            "order": order_id,
            "v1": (decision_v1(plain), decision_v1(pushy)),
            "v2": (decision_v2(plain, order_id), decision_v2(pushy, order_id)),
        })
    return rows


if __name__ == "__main__":
    rows = pressure_report()
    for r in rows:
        flag = lambda pair: "CHANGED" if pair[0] != pair[1] else "same"
        print(f"#{r['order']}  ch01 handler: {r['v1'][0]} -> {r['v1'][1]} ({flag(r['v1'])})"
              f"  |  handle_v2: {r['v2'][0]} -> {r['v2'][1]} ({flag(r['v2'])})")
    changed_v1 = sum(r["v1"][0] != r["v1"][1] for r in rows)
    changed_v2 = sum(r["v2"][0] != r["v2"][1] for r in rows)
    print(f"decisions changed by pressure: ch01 handler {changed_v1}, handle_v2 {changed_v2}")
    # self-test (run_solutions.py relies on these)
    assert changed_v1 >= 1, "the stub is scripted to give in to pressure"
    assert changed_v2 == 0, "decide() in code holds regardless of tone"
    print("ch02 solution: OK")

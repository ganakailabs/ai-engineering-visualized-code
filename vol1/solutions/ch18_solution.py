"""Chapter 18 exercise: check the router.

1. Route the four demo tickets and say which rung each one needs.
2. Swap in a router model that answers "refunds, probably". What does route() do?
3. Which ticket type would you move up to an agent, and why?
Run: python3 vol1/solutions/ch18_solution.py
"""
import _path  # noqa: F401
from _path import STUB, DECISIONS  # noqa: F401
from ch18 import RUNG, route

if __name__ == "__main__":
    tickets = ("Refund for #4410, please", "Where is my parcel?",
               "My NW-500 battery stopped charging", "Can you change my delivery address?")
    labels = [route(t)[0] for t in tickets]
    print("labels:", labels)
    sloppy = lambda messages, **kw: {"text": "refunds, probably"}
    fallback = route("Refund for #4410, please", model=sloppy)
    print("sloppy router:", fallback)
    print("rungs:", RUNG)
    assert set(labels) <= {"refund", "tracking", "warranty", "other"}, "only allowed labels"
    if STUB:
        assert labels == ["refund", "tracking", "warranty", "other"]
    assert fallback == ("other", "escalate: passed to a person"), "an unknown label goes to a person"
    assert not route("Refund for #4410, please")[1].startswith("approve"), "final sale is never approved"
    if STUB:
        assert route("Refund for #4410, please")[1] == "deny (R3)"
    print("ch18 solution: OK")

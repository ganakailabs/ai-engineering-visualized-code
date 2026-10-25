"""Chapter 4 exercise: split the meter.

Count the input tokens of one call slice by slice (rules + policy, history, ticket),
biggest first, for the long thread in ch04.py. Then pack the same thread with
pack_context() and count again: which slice shrank, and which never did?
Run: python3 vol1/solutions/ch04_solution.py
"""
import _path  # noqa: F401  (adds vol1/ to the import path)
from ch04 import EXAMPLE_RATES, PRICE_PER_MILLION, cost, pack_context
from stub_model import rough_token_count  # placeholder counter: use your provider's
from store import policy_text

RULES = "You decide refund requests. Reply as '<approve|deny|escalate>: <reason>'."
TICKET = "So, refund for it or not?"


def long_thread(turns=40):  # the same pasted-email thread as ch04.py
    history = []
    for i in range(turns):
        history.append({"role": "user", "content": f"Email {i}: still waiting on order #1234, see thread below. " * 3})
        history.append({"role": "assistant", "content": "Sorry for the wait. Checking now."})
    return history


def slices(system_text, history, ticket):
    counts = {
        "rules + policy": rough_token_count(system_text),
        "history": sum(rough_token_count(t["content"]) for t in history),
        "ticket": rough_token_count(ticket),
    }
    return dict(sorted(counts.items(), key=lambda kv: kv[1], reverse=True))


if __name__ == "__main__":
    history = long_thread()
    full = slices(RULES + "\n" + policy_text(), history, TICKET)
    print("send everything :", full, "| total", sum(full.values()))

    msgs, used, dropped = pack_context(RULES, policy_text(), history, TICKET,
                                       window=2000, reserve_output=300,
                                       notes="order_id=1234; customer asked for refund on turn 1")
    packed = slices(msgs[0]["content"], msgs[1:-1], msgs[-1]["content"])
    print("packed (2000/300):", packed, "| total", sum(packed.values()), "| turns dropped", dropped)
    # self-test (run_solutions.py relies on these)
    assert next(iter(full)) == "history", "history is the biggest slice of a long thread"
    assert packed["history"] < full["history"] and dropped > 0
    assert packed["ticket"] == full["ticket"], "the ticket is never trimmed"
    assert packed["rules + policy"] >= full["rules + policy"], "rules and policy are never trimmed"
    assert sum(packed.values()) <= 2000 - 300, "room for the answer stays free"
    # real prices stay empty; the made-up example rates show the arithmetic
    u = {"input_tokens": 1_000_000, "output_tokens": 1_000_000}
    assert cost(u) is None and set(PRICE_PER_MILLION.values()) == {None}
    assert cost(u, EXAMPLE_RATES) == EXAMPLE_RATES["input"] + EXAMPLE_RATES["output"]
    print("ch04 solution: OK")

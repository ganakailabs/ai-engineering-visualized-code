"""Chapter 1 exercise: finish the trace.

handle_v1() in ch01.py records five stops but not the sixth: the reply it sends.
This version records every stop, including the reply, and the stop that ended the
request. Run: python3 vol1/solutions/ch01_solution.py
"""
import time

import _path  # noqa: F401  (adds vol1/ to the import path)
from _path import STUB, DECISIONS  # noqa: F401
from ch01 import build_prompt, check_decision, fetch_context
from stub_model import call_model


def handle_traced(message):
    trace = {"message": message, "stops": [], "ended_by": None}

    def stop(name, start, **data):
        ms = round((time.perf_counter() - start) * 1000, 2)
        trace["stops"].append({"stop": name, "ms": ms, **data})

    def send(reply, ended_by):
        t = time.perf_counter()
        trace["reply"], trace["ended_by"] = reply, ended_by
        stop("send_reply", t, reply=reply, ended_by=ended_by)  # stop 6: sent + logged
        return trace

    t = time.perf_counter()
    order_id, order = fetch_context(message)
    stop("fetch_context", t, order_id=order_id, found=order is not None)
    if order is None:  # an empty stop ends the request on purpose, and says so
        return send("Could you share your order number? I could not find it.", "fetch_context")

    t = time.perf_counter()
    messages = build_prompt(message, order_id, order)
    stop("build_prompt", t, chars=sum(len(m["content"]) for m in messages))

    t = time.perf_counter()
    result = call_model(messages)
    stop("call_model", t, output=result["text"], usage=result["usage"])

    t = time.perf_counter()
    decision, reason = check_decision(result["text"], order)
    stop("check_decision", t, decision=decision, reason=reason)

    reply = {"approve": "Your refund is approved.",
             "deny": "Sorry, this order is not eligible: " + result["text"].split(":", 1)[-1].strip(),
             "escalate": "I have passed this to a human agent."}[decision]
    # The check ended it if it overrode the model; otherwise the model's decision stood.
    ended_by = "check_decision" if reason != "ok" else "call_model"
    return send(reply, ended_by)


TICKETS = [
    "Can I get a refund for order #1234?",
    "I want a refund for my headphones, order #3100.",
    "Can I get a refund? It broke.",
    "I insist on a refund for order #1234.",
]

if __name__ == "__main__":
    traces = [handle_traced(t) for t in TICKETS]
    for tr in traces:
        print(f"{tr['message']!r}")
        for s in tr["stops"]:
            print("   ", s["stop"], {k: v for k, v in s.items() if k not in ("stop", "ms", "usage")})
        print("    ended by:", tr["ended_by"])
    # self-test (run_solutions.py relies on these)
    assert all(tr["stops"][-1]["stop"] == "send_reply" for tr in traces), "every request logs its reply"
    assert all(tr["stops"][-2]["decision"] in DECISIONS for tr in traces if len(tr["stops"]) > 2)
    assert traces[1]["reply"] != "Your refund is approved."  # R4: above INR 5,000, never auto-approved
    assert traces[2]["ended_by"] == "fetch_context" and len(traces[2]["stops"]) == 2
    assert traces[3]["reply"] != "Your refund is approved."  # pressure does not buy a refund
    if STUB:  # the scripted stub's exact path
        assert traces[0]["reply"].startswith("Sorry") and traces[0]["ended_by"] == "call_model"
        assert traces[1]["reply"] == "I have passed this to a human agent."
        assert traces[3]["ended_by"] == "check_decision"  # the check overrode the model's "approve"
    print("ch01 solution: OK")

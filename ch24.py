"""Chapter 24: Ship It: Errors, Tracing, Latency and the Complete System."""
import json

from ch15 import augment, generate, index, retrieve
from ch16 import grounded, passage_gate


# MM-064: timeout, retry, give up. A scripted provider that fails twice.
class Transient(Exception):            # rate limit, server error, timeout
    pass


class Permanent(Exception):            # bad request, bad key: retry won't help
    pass


def flaky(script):
    """A fake provider call that fails as the script says, then answers."""
    script = list(script)

    def call(ticket, timeout):
        kind = script.pop(0) if script else "ok"
        if kind == "rate_limit":
            raise Transient("429 rate limit")
        if kind == "timeout":
            raise Transient(f"no reply in {timeout} s")
        if kind == "bad_request":
            raise Permanent("400 bad request")
        return grounded(ticket)[0]
    return call


GIVE_UP = "escalate: we are busy right now; a person will reply soon."


def call_with_retry(call, ticket, tries=3, wait=1.0, timeout=10,
                    sleep=None, log=print):
    for n in range(1, tries + 1):
        try:
            return call(ticket, timeout=timeout)
        except Transient as e:
            log(f"try {n}: {e}")
            if n < tries:
                sleep(wait * 2 ** (n - 1))      # 1 s, 2 s, 4 s ...
        except Permanent as e:
            log(f"try {n}: {e} (not retried)")
            break
    return GIVE_UP


# MM-065: the debug replay. Store what the model saw, not just what it said.
def record(ticket):
    passages = retrieve(ticket, index())
    prompt = augment(passages)
    reply = generate(prompt, ticket)
    ok, why = passage_gate(reply, passages)
    return {"ticket": ticket, "model": "stub-large", "prompt": prompt,
            "passages": list(passages), "reply": reply, "gate": why}


def replay(rec):
    """Send the stored prompt again; same input, same output?"""
    return generate(rec["prompt"], rec["ticket"]) == rec["reply"]


# MM-066: the latency budget. Made-up timings for the demo, in ms.
BUDGET_MS = 3000
TIMINGS = {"input checks": 20, "retrieve": 180, "model": 2400,
           "citation gate": 15, "output checks": 25, "logs": 10}


def over_budget(timings=TIMINGS, budget=BUDGET_MS):
    total = sum(timings.values())
    slowest = max(timings, key=timings.get)
    return total, slowest, total > budget


# MM-067: the complete Vol 1 diagram, as a checklist
DIAGRAM = {"INPUT": "ch03 messages_good, ch23 check_in",
           "CONTEXT": "ch10 build_messages, ch15 augment",
           "KNOWLEDGE": "ch13 hybrid, ch14 chunk, ch15 retrieve",
           "MODEL": "stub_model call_model",
           "TOOLS": "ch11 run_tool, ch19 run_agent, ch22 guard",
           "CHECK": "ch07 citation_gate, ch11 check, ch16 passage_gate",
           "REPLY": "ch23 check_out, ch24 call_with_retry",
           "LOGS": "ch04 log_usage, ch24 record",
           "EVALS": "ch08 score, ch17 scorecards"}

if __name__ == "__main__":
    q = "My NW-500 battery stopped charging. Is it under warranty?"
    waits = []
    print(call_with_retry(flaky(["rate_limit", "timeout"]), q,
                          sleep=waits.append))
    print("waited:", waits)
    print(call_with_retry(flaky(["rate_limit"] * 3), q, sleep=waits.append))
    print(call_with_retry(flaky(["bad_request"]), q, sleep=waits.append))
    rec = record(q)
    print("log record:", json.dumps(rec)[:72], "...")
    print("replay matches:", replay(rec))
    print("latency (total ms, slowest box, over budget):", over_budget())
    for box, where in DIAGRAM.items():
        print(f"  {box:10} {where}")

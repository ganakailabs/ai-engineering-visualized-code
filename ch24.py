"""Chapter 24: Ship It: Errors, Tracing, Latency and the Complete System."""
import json
import time

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
                    deadline=30.0, sleep=time.sleep,
                    clock=time.monotonic,
                    log=print):
    """Bounded retry: at most `tries` calls and `deadline` seconds in total.
    The timeout is passed to the provider call; this helper does not interrupt
    a call that hangs (a real client library or thread must do that)."""
    start = clock()
    for n in range(1, tries + 1):
        try:
            return call(ticket, timeout=timeout)
        except Transient as e:
            log(f"try {n}: {e}")
            pause = wait * 2 ** (n - 1)             # 1 s, 2 s, 4 s ...
            if n == tries or clock() - start + pause > deadline:
                break                     # out of tries or time
            sleep(pause)
        except Permanent as e:
            log(f"try {n}: {e} (not retried)")
            break
    return GIVE_UP


# MM-064: a retried WRITE needs an idempotency key. Here the refund is made,
# but the reply is lost on the way back, so the caller retries.
class RefundService:
    def __init__(self):
        self.paid, self.seen, self.lose_next_reply = [], {}, True

    def refund(self, order_id, amount, key=None):
        if key is not None and key in self.seen:
            return self.seen[key]         # same key: pay once
        self.paid.append((order_id, amount))   # money moves
        result = f"refunded INR {amount:,} on #{order_id}"
        if key is not None:
            self.seen[key] = result
        if self.lose_next_reply:
            self.lose_next_reply = False
            raise Transient("reply lost after the refund was made")
        return result


def refund_with_retry(service, order_id, amount, key=None):
    for _ in range(2):
        try:
            return service.refund(order_id, amount, key=key)
        except Transient:
            continue
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
    """Send the stored prompt again and compare. The stub is scripted, so it
    matches; a hosted model may word it differently: compare, don't assume."""
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
    for key in (None, "refund-3100-ticket-88"):
        svc = RefundService()
        refund_with_retry(svc, "3100", 12500, key=key)
        print(f"retry after lost reply, key={key}: payments={svc.paid}")
    print("latency (total ms, slowest box, over budget):", over_budget())
    for box, where in DIAGRAM.items():
        print(f"  {box:10} {where}")

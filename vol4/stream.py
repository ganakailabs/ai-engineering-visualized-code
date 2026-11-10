"""Chapter 8: streaming, cancellation and backpressure.

MM-164 The Stream Contract: which events and partial text may go out before the checks
       run (status and neutral text), and what only the checked final message may say
       (any decision: refund, replacement, denial).
MM-165 Backpressure: downstream capacity limits upstream intake. A bounded queue admits
       only what the workers can finish inside the SLO; the rest get a retry signal.

Teaching choices, said out loud:
- the stream is an in-process list of server-sent events (id, event, data), written in
  the text/event-stream wire format; no socket is opened, so no network timing is shown;
- the model's draft is fixed text (the stub), so the lesson is the contract, not wording;
- the flood is a seeded, simulated arrival schedule; service time is a lab number.
"""
import math
import re

import _root  # noqa: F401

from service import refund_rule
from store import ORDERS
from world import OWNERS

# Fixture delivery addresses (fictional), the personal data a delivery update may touch.
ADDRESSES = {"asha": "14 Lake View Road, Pune", "c-42": "7 Hill Street, Nashik"}

# ---------------- MM-164 the stream contract ----------------

# Partial text may only come from this list: status a customer can read early.
NEUTRAL = {"started": "Got it. Looking at your ticket now.",
           "order": "Checking your order...",
           "policy": "Reading the refund policy...",
           "check": "Checking the reply before sending..."}
# Decision words: allowed only in the final, checked message.
DECISION = re.compile(r"\b(approved?|refund(ed)? of|denied|replace(ment)?|"
                      r"cannot be (refunded|returned))\b", re.I)


class Stream:
    """Events with increasing ids, kept so a client can resume after a drop."""

    def __init__(self):
        self.events = []

    def emit(self, event, data):
        e = {"id": len(self.events) + 1, "event": event, "data": data}
        self.events.append(e)
        return e

    def since(self, last_id):
        """What a client that saw up to last_id has not seen yet (Last-Event-ID)."""
        return [e for e in self.events if e["id"] > last_id]


def sse(e):
    """One event in the text/event-stream wire format."""
    return f"id: {e['id']}\nevent: {e['event']}\ndata: {e['data']}\n\n"


def draft(order_id):
    """The stub model's draft reply: it always offers the refund (the risky draft)."""
    o = ORDERS[order_id]
    return f"Your refund of INR {o['amount']:,} for order #{order_id} is approved."


def check_output(order_id, text):
    """The output check: no other customer's personal data (privacy, checked first,
    on every reply, decision or not), and any decision must match the records."""
    owner = OWNERS.get(order_id)
    if any(addr in text for cust, addr in ADDRESSES.items() if cust != owner):
        return False, "privacy"
    o = ORDERS[order_id]
    ok, clause = refund_rule(o)
    if DECISION.search(text) and "approved" in text:
        if not ok:
            return False, clause
        if o["amount"] > 5000:
            return False, "R4"
    return True, clause


FINAL_BLOCKED = {"R3": "Order #{oid} is final sale, so it cannot be refunded (R3).",
                 "R4": "Refunds above INR 5,000 need a support agent's approval (R4). "
                       "We have passed order #{oid} to them.",
                 "R1": "Order #{oid} is past the 30-day refund window (R1).",
                 "R2": "Order #{oid} is past the 7-day window for damaged items (R2).",
                 "privacy": "Your order #{oid} is on its way. We will message you when "
                            "it is out for delivery."}


def delivery_stream(order_id, text):
    """A delivery update decides nothing, but generated text can still disclose
    personal data. Only fixed status lines go early; the generated text waits for
    check_output(), like a decision."""
    s = Stream()
    s.emit("started", NEUTRAL["started"])
    s.emit("working", NEUTRAL["order"])
    s.emit("working", NEUTRAL["check"])
    ok, clause = check_output(order_id, text)
    s.emit("final", text if ok else FINAL_BLOCKED[clause].format(oid=order_id))
    s.emit("done", "")
    return s, ok, clause


def naive_stream(order_id, words_per_event=3):
    """Pipe the draft out as it is written, then check: the customer saw it first."""
    s, text = Stream(), draft(order_id)
    words = text.split()
    for i in range(0, len(words), words_per_event):
        s.emit("partial", " ".join(words[i:i + words_per_event]))
    ok, clause = check_output(order_id, text)
    s.emit("final", text if ok else FINAL_BLOCKED[clause].format(oid=order_id))
    return s, ok, clause


def contract_stream(order_id):
    """Status and neutral text first; the decision only in the checked final."""
    s = Stream()
    s.emit("started", NEUTRAL["started"])
    s.emit("working", NEUTRAL["order"])
    s.emit("working", NEUTRAL["policy"])
    text = draft(order_id)
    s.emit("working", NEUTRAL["check"])
    ok, clause = check_output(order_id, text)
    s.emit("final", text if ok else FINAL_BLOCKED[clause].format(oid=order_id))
    s.emit("done", "")
    return s, ok, clause


def decision_before_final(stream):
    """The contract test: no event before 'final' may carry decision words."""
    return [e for e in stream.events if e["event"] != "final" and DECISION.search(e["data"])]


# ---------------- cancellation at a safe state ----------------

STEPS = ["lookup", "decide", "pay", "record", "reply"]
UNSAFE_AFTER = {"pay": "record"}      # once paying starts, finish recording before stopping


def run_with_cancel(cancel_after):
    """Run the job's steps; a cancel is honoured only at a safe state between steps.
    Returns the steps that ran. Cancelling after 'pay' still runs 'record'."""
    ran, cancelled = [], False
    for step in STEPS:
        if cancelled and not (ran and UNSAFE_AFTER.get(ran[-1]) == step):
            break
        ran.append(step)
        if step == cancel_after:
            cancelled = True
    return ran


# ---------------- MM-165 backpressure ----------------

def workers_needed(per_min, service_s, max_util):
    """Average busy workers = arrival rate x service time (Little's law);
    divide by the utilisation you are willing to run at, round up."""
    busy = per_min / 60 * service_s
    return busy, math.ceil(busy / max_util - 1e-9)


def queue_limit(workers, service_s, deadline_s):
    """How many may wait so each still gets its first checked reply within the deadline:
    one wave is in service, and each wave ahead adds service_s."""
    return workers * (deadline_s // service_s - 1)


def simulate(per_min, minutes, workers, service_s, deadline_s, bounded=True, tail=None):
    """Seconds-step simulation (all simulated). Arrivals are spread evenly.
    Returns per-ticket outcomes: admitted or refused, and first-reply time.
    tail=(every, slow_s): every `every`-th ticket takes slow_s instead of service_s
    (a deterministic long tail); the queue limit is still sized on service_s."""
    limit = queue_limit(workers, service_s, deadline_s) if bounded else 10 ** 9
    arrivals, acc = [], 0.0
    for t in range(minutes * 60):
        acc += per_min / 60
        while acc >= 1:
            arrivals.append(t)
            acc -= 1
    queue, busy, out, done = [], [], {}, []
    i = 0
    t = 0
    while i < len(arrivals) or queue or busy:
        for job in [b for b in busy if b[1] <= t]:
            busy.remove(job)
            done.append(job[0])
            out[job[0]]["reply_s"] = t - out[job[0]]["arrived"]
        while i < len(arrivals) and arrivals[i] == t:
            tid = f"T-{i:04d}"
            if len(queue) < limit:
                queue.append(tid)
                out[tid] = {"arrived": t, "admitted": True}
            else:
                out[tid] = {"arrived": t, "admitted": False, "retry_after_s": service_s}
            i += 1
        while queue and len(busy) < workers:
            tid = queue.pop(0)
            dur = service_s
            if tail and int(tid[2:]) % tail[0] == tail[0] - 1:
                dur = tail[1]
            busy.append((tid, t + dur))
        t += 1
    return out, done

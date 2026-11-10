"""Chapter 3: Observability: Traces, Metrics and Logs.

Run from the repo root:  python3 vol4/ch03.py
Traces Asha's refund ticket across the API and a worker (the trace id crosses the
queue in a W3C traceparent), exports the spans as OTLP/JSON to vol4/runs/, measures
span completeness on a simulated Tuesday, and writes one log record through the
redacting sink. Durations, drops and token counts are simulated or come from the
Vol 1 placeholder token counter; none is a measurement of a real system.
"""
import json
import random
import tempfile
from pathlib import Path

import _root  # noqa: F401

import logsink
import trace
from stub_model import rough_token_count

RUNS = Path(__file__).resolve().parent / "runs"
PROMPT = ("Policy R2: damaged items, refund or replace within 7 days of delivery. "
          "Order #2001 ceramic mug set INR 950 delivered 2026-10-01, damaged. "
          "Ticket: my mug set arrived chipped, refund please.")
REPLY = '{"action": "refund", "order_id": "2001", "clause": "R2"}'
FLOOR = 0.95                                  # completeness below this: withhold metrics


def one_ticket(tr, t0, ticket_id="T-2001-a", job_ms=1850.0, drop_worker=False):
    """API span in one process; the job span in another, joined by traceparent."""
    api = tr.start("POST /tickets", "SERVER", service="api", start_ns=t0,
                   attrs={"http.request.method": "POST", "http.route": "/tickets",
                          "http.response.status_code": 202, "ticket.id": ticket_id})
    tr.end(api, 12.0)
    carried = trace.traceparent(api)            # stored on the job row with the ticket
    if drop_worker:
        return api, None
    w0 = api["end_ns"] + 40_000_000             # 40 ms in the queue (simulated)
    job = tr.start("process tickets", "CONSUMER", parent=carried, start_ns=w0,
                   attrs={"job.id": f"op-a-{ticket_id}"})
    step = tr.start("invoke_agent northwind-assistant", parent=job, start_ns=w0 + 1_000_000,
                    attrs={"gen_ai.operation.name": "invoke_agent",
                           "gen_ai.agent.name": "northwind-assistant"})
    ret = tr.start("retrieval", parent=step, start_ns=step["start_ns"],
                   attrs={"gen_ai.operation.name": "retrieval", "gen_ai.retrieval.top_k": 3})
    tr.end(ret, 35.0)
    chat = tr.start("chat stub", "CLIENT", parent=step, start_ns=ret["end_ns"],
                    attrs={"gen_ai.operation.name": "chat",
                           "gen_ai.provider.name": "northwind.stub",
                           "gen_ai.request.model": "stub",
                           "gen_ai.usage.input_tokens": rough_token_count(PROMPT),
                           "gen_ai.usage.output_tokens": rough_token_count(REPLY)})
    tr.end(chat, job_ms - 35.0 - 120.0 - 2.0)
    tool = tr.start("execute_tool issue_refund", parent=step, start_ns=chat["end_ns"],
                    attrs={"gen_ai.operation.name": "execute_tool",
                           "gen_ai.tool.name": "issue_refund",
                           "operation.id": f"op-a-{ticket_id}/refund-2001"})
    tr.end(tool, 120.0)
    tr.end(step, (tool["end_ns"] - step["start_ns"]) / 1e6)
    tr.end(job, (step["end_ns"] - job["start_ns"]) / 1e6 + 1.0)
    return api, job


def p95(values):
    """Nearest-rank 95th percentile."""
    v = sorted(values)
    return v[max(0, -(-95 * len(v) // 100) - 1)]


def tuesday(seed=5, jobs=30, slow=10, truth=None):
    """30 jobs; the 10 slow ones ran on a worker whose exporter lost its buffer when
    the process was restarted, so their worker spans never arrived (simulated)."""
    rng, tr = random.Random(seed), trace.Tracer(seed)
    for i in range(jobs):
        is_slow = i % 3 == 0 and slow > 0
        slow -= is_slow
        ms = rng.uniform(9000, 30000) if is_slow else rng.uniform(1200, 2600)
        if truth is not None:
            truth.append(ms / 1000)               # known to the simulator, not to the viewer
        one_ticket(tr, trace.T0_NS + i * 60_000_000_000, f"T-3{i:03d}-a", ms,
                   drop_worker=is_slow)
    return tr.spans, jobs


if __name__ == "__main__":
    print("== Part 1: one ticket, one trace (MM-120) ==")
    tr = trace.Tracer()
    api, job = one_ticket(tr, trace.T0_NS)
    print(f"trace {api['trace_id']} (seeded; real ids are random)")
    print("durations simulated")
    for line in trace.tree(tr.spans, api["trace_id"]):
        print("  " + line)
    chat = next(s for s in tr.spans if s["name"] == "chat stub")
    print(f"chat tokens in={chat['attrs']['gen_ai.usage.input_tokens']} "
          f"out={chat['attrs']['gen_ai.usage.output_tokens']} (placeholder counter)")
    doc = trace.to_otlp(tr.spans)
    RUNS.mkdir(exist_ok=True)
    (RUNS / "ch03-trace.otlp.json").write_text(trace.dumps(doc))
    problems = trace.check_otlp(doc)
    print(f"export otlp {'ok' if not problems else problems} "
          f"({len(tr.spans)} spans, {len(doc['resourceSpans'])} services) "
          f"-> vol4/runs/ch03-trace.otlp.json")

    for label, bad in (("all-zero trace id", "00-" + "0" * 32 + "-" + "1" * 16 + "-01"),
                       ("not hex", "00-hello-world-01")):
        span = trace.Tracer(seed=9).start("POST /tickets", "SERVER", parent=bad)
        print(f"incoming traceparent, {label} -> "
              f"{'new trace started' if span['attrs'].get('trace.restarted') else 'joined'}")

    print("\n== Part 2: the missing spans (simulated Tuesday) ==")
    truth = []
    spans, jobs = tuesday(truth=truth)
    received = [s for s in spans if s["name"] == "process tickets"]
    times = [(s["end_ns"] - s["start_ns"]) / 1e9 for s in received]
    print(f"jobs in queue table={jobs} worker spans received={len(received)}")
    print(f"naive p95 job time={p95(times):.1f}s from {len(received)} spans "
          f"(looks better; simulated)")
    print(f"true p95 job time={p95(truth):.1f}s from all {jobs} jobs "
          f"(only the simulator knows)")
    completeness = len(received) / jobs
    verdict = "metric withheld" if completeness < FLOOR else "metric published"
    print(f"completeness worker={completeness:.2f} floor={FLOOR} -> {verdict}")

    print("\n== Part 3: what to log (MM-121) ==")
    record = {"event": "reply_sent", "ticket_id": "T-2001-a", "tenant_id": "a",
              "customer": "Asha Rao", "ticket_text": "My mug set arrived chipped.",
              "note": "customer asked for a call on +91 98765 43210, "
                      "copy to asha.rao@example.com", "amount_inr": 950}
    tmp = Path(tempfile.mkdtemp(prefix="aiev-v4-ch03-"))
    raw = logsink.Sink(tmp / "raw.log", redacting=False)
    raw.write(record)
    print(f"no redaction: scan finds {len(logsink.scan(raw.path))} items")
    sink = logsink.Sink(tmp / "app.log")
    written = json.loads(sink.write(record))
    print("log written:")
    for k, v in written.items():
        print(f"  {k}: {v}")
    print(f"redacting sink: scan finds {len(logsink.scan(sink.path))} items")
    other = logsink.Sink(tmp / "addr.log")
    kept = json.loads(other.write({"event": "note", "note": "leave it at flat 4B, 12 Lake Road"}))
    print(f"an address is outside the patterns: written "
          f"{'as-is' if 'Lake Road' in kept['note'] else 'masked'}, "
          f"scan finds {len(logsink.scan(other.path))}")

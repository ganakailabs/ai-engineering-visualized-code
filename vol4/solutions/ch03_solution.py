"""Chapter 3 exercise: Follow the id to the courier.

The agent step books a courier pickup through an MCP tools/call. Put the trace
context in the request's params._meta (MCP 2026-07-28 documents traceparent,
tracestate and baggage there), not in the prompt. The courier server reads it and
starts its span as a child of the caller's span. Predict first: where does the
courier span appear in the tree?

The courier server here is a stdlib stand-in for the Vol 2 courier server, so the
exercise runs without the MCP SDK; the message shape is Vol 2's mcp_toy.request.
"""
import _path  # noqa: F401

import ch03
import mcp_toy
import trace

tr = trace.Tracer()
api, job = ch03.one_ticket(tr, trace.T0_NS)
step = next(s for s in tr.spans if s["name"].startswith("invoke_agent"))


def courier_server(message, tracer):
    """Server side: the parent comes from params._meta, if the caller sent one."""
    meta = message["params"].get("_meta", {})
    span = tracer.start("tools/call book_pickup", "SERVER", parent=meta.get("traceparent"),
                        service="courier", start_ns=step["end_ns"] + 2_000_000,
                        attrs={"mcp.method.name": "tools/call",
                               "gen_ai.tool.name": "book_pickup"})
    return tracer.end(span, 80.0)


client = tr.start("tools/call book_pickup", "CLIENT", parent=step, start_ns=step["end_ns"],
                  attrs={"mcp.method.name": "tools/call", "gen_ai.tool.name": "book_pickup"})
msg = mcp_toy.request(7, "tools/call", {"name": "book_pickup",
                                        "arguments": {"order_id": "2001"}})
msg["params"]["_meta"]["traceparent"] = trace.traceparent(client)   # the fix
server = courier_server(msg, tr)
tr.end(client, 84.0)
tr.end(step, (client["end_ns"] - step["start_ns"]) / 1e6)
tr.end(job, (step["end_ns"] - job["start_ns"]) / 1e6 + 1.0)

for line in trace.tree(tr.spans, api["trace_id"]):
    print("  " + line)
doc = trace.to_otlp(tr.spans)
assert trace.check_otlp(doc) == []
exported = {s["spanId"]: s for rs in doc["resourceSpans"]
            for ss in rs["scopeSpans"] for s in ss["spans"]}
srv = next(s for s in exported.values() if s["kind"] == trace.KIND["SERVER"]
           and s["name"] == "tools/call book_pickup")
assert srv["traceId"] == api["trace_id"]
assert srv["parentSpanId"] == client["span_id"]
assert exported[client["span_id"]]["parentSpanId"] == step["span_id"]
assert "traceparent" not in str(msg["params"]["arguments"])      # metadata, not content
print("courier span: child of the tools/call client span, under the agent step")
print("ch03 solution: OK")

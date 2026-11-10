"""Optional: parse the Chapter 3 export with the official OpenTelemetry protobuf types.

Needs `pip install opentelemetry-proto` (checked with 1.45.2). Skips, and passes, when
it is not installed: the book's code stays stdlib-only. OTLP/JSON carries trace and
span ids as hex; protobuf's generic JSON parser expects base64 for bytes fields, so
the ids are converted before parsing (the OTLP specification describes this difference).
"""
import _path  # noqa: F401

import base64
import copy

import ch03
import trace

try:
    from google.protobuf import json_format
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import \
        ExportTraceServiceRequest
except ImportError:
    print("test_otlp_proto: SKIPPED (opentelemetry-proto not installed)")
    raise SystemExit(0)

tr = trace.Tracer()
ch03.one_ticket(tr, trace.T0_NS)
doc = copy.deepcopy(trace.to_otlp(tr.spans))
for rs in doc["resourceSpans"]:
    for ss in rs["scopeSpans"]:
        for s in ss["spans"]:
            for k in ("traceId", "spanId", "parentSpanId"):
                if k in s:
                    s[k] = base64.b64encode(bytes.fromhex(s[k])).decode()
msg = json_format.ParseDict(doc, ExportTraceServiceRequest())
got = [s for r in msg.resource_spans for ss in r.scope_spans for s in ss.spans]
assert len(got) == 6
assert {s.name for s in got} >= {"POST /tickets", "chat stub", "retrieval"}
assert all(len(s.trace_id) == 16 and len(s.span_id) == 8 for s in got)
print("test_otlp_proto: OK (parsed as ExportTraceServiceRequest)")

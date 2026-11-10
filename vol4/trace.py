"""Chapter 3: a stdlib span tracer with an OpenTelemetry (OTLP/JSON) export.

MM-120 Nested Spans: one request is a tree of timed spans (API, job, agent step,
       retrieval, model call, tool call) that share one trace id.

Teaching choices, said out loud:
- ids come from a seeded generator so the book's output repeats; real tracers use
  random ids (W3C Trace Context asks for randomness in trace ids);
- times are simulated nanoseconds from the book's date, not wall-clock times;
- span names and gen_ai.* attributes follow the OpenTelemetry GenAI semantic
  conventions, whose status is Development (checked Nov 4, 2026): names may change.
"""
import json
import random
import re

_TP = re.compile(r"^([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def parse_traceparent(value):
    """W3C Trace Context checks on an incoming traceparent. Returns (trace_id,
    parent_id), or None when the value is malformed: wrong shape, upper-case hex,
    version ff, or an all-zero trace id or parent id. On None the caller starts a
    new trace. A valid header from outside is still client-controlled metadata:
    whether to continue its trace is a trust decision, not a parsing one."""
    m = _TP.match(value or "")
    if not m:
        return None
    version, trace_id, parent_id, _ = m.groups()
    if version == "ff" or set(trace_id) == {"0"} or set(parent_id) == {"0"}:
        return None
    return trace_id, parent_id

KIND = {"INTERNAL": 1, "SERVER": 2, "CLIENT": 3, "PRODUCER": 4, "CONSUMER": 5}
T0_NS = 1_791_108_000_000_000_000          # 2026-10-04 10:00:00 UTC, the book's TODAY


class Tracer:
    def __init__(self, seed=3):
        self.rng, self.spans = random.Random(seed), []

    def _hex(self, n_bytes):
        return "".join(f"{self.rng.randrange(256):02x}" for _ in range(n_bytes))

    def start(self, name, kind="INTERNAL", parent=None, service="worker",
              start_ns=T0_NS, attrs=None):
        """parent is a span dict or a W3C traceparent string from another process.
        A malformed traceparent starts a new trace (marked trace.restarted)."""
        attrs = dict(attrs or {})
        ctx = parse_traceparent(parent) if isinstance(parent, str) else None
        if isinstance(parent, str) and ctx is None:
            trace_id, parent_id = self._hex(16), ""
            attrs["trace.restarted"] = True
        elif ctx:
            trace_id, parent_id = ctx
        elif parent:
            trace_id, parent_id = parent["trace_id"], parent["span_id"]
        else:
            trace_id, parent_id = self._hex(16), ""
        span = {"trace_id": trace_id, "span_id": self._hex(8), "parent_id": parent_id,
                "name": name, "kind": kind, "service": service, "start_ns": start_ns,
                "end_ns": start_ns, "attrs": attrs}
        self.spans.append(span)
        return span

    @staticmethod
    def end(span, duration_ms):
        span["end_ns"] = span["start_ns"] + int(duration_ms * 1_000_000)
        return span


def traceparent(span):
    """W3C Trace Context header value:
    version-traceid-parentid-flags (01 = sampled)."""
    return f"00-{span['trace_id']}-{span['span_id']}-01"


def tree(spans, trace_id):
    """Indented lines, children under parents, ordered by start time."""
    mine = [s for s in spans if s["trace_id"] == trace_id]
    ids = {s["span_id"] for s in mine}
    lines = []

    def walk(parent, depth):
        for s in sorted((s for s in mine if s["parent_id"] == parent),
                        key=lambda s: s["start_ns"]):
            ms = (s["end_ns"] - s["start_ns"]) / 1e6
            label = "  " * depth + s["name"]
            lines.append(f"{label:<40}{ms:>8.1f} ms")
            walk(s["span_id"], depth + 1)
    walk("", 0)
    for s in mine:                                     # orphans: parent never arrived
        if s["parent_id"] and s["parent_id"] not in ids:
            lines.append(f"? {s['name']} (parent {s['parent_id'][:8]}... missing)")
    return lines


# ---- OTLP/JSON export (OTLP spec 1.11.1: hex ids, enum kinds as integers) ----------

def _value(v):
    if isinstance(v, bool):
        return {"boolValue": v}
    if isinstance(v, int):
        return {"intValue": str(v)}                    # int64 is a string in JSON
    if isinstance(v, float):
        return {"doubleValue": v}
    return {"stringValue": str(v)}


def to_otlp(spans):
    by_service = {}
    for s in spans:
        by_service.setdefault(s["service"], []).append(s)
    return {"resourceSpans": [{
        "resource": {"attributes": [{"key": "service.name",
                                     "value": {"stringValue": f"northwind-{svc}"}}]},
        "scopeSpans": [{
            "scope": {"name": "aiev.vol4.trace", "version": "0.1.0"},
            "spans": [{
                "traceId": s["trace_id"], "spanId": s["span_id"],
                **({"parentSpanId": s["parent_id"]} if s["parent_id"] else {}),
                "name": s["name"], "kind": KIND[s["kind"]],
                "startTimeUnixNano": str(s["start_ns"]), "endTimeUnixNano": str(s["end_ns"]),
                "attributes": [{"key": k, "value": _value(v)} for k, v in s["attrs"].items()],
                "status": {}} for s in group]}]}
        for svc, group in by_service.items()]}


def check_otlp(doc):
    """A stdlib shape check of an ExportTraceServiceRequest in OTLP/JSON. Returns a list
    of problems (empty = ok). tests/test_otlp_proto.py also parses it with the official
    opentelemetry-proto package when that is installed."""
    problems = []
    is_hex = lambda x, n: len(x) == n and all(c in "0123456789abcdef" for c in x)
    for rs in doc.get("resourceSpans", []):
        for ss in rs.get("scopeSpans", []):
            for sp in ss.get("spans", []):
                if not is_hex(sp.get("traceId", ""), 32) or set(sp["traceId"]) == {"0"}:
                    problems.append(f"{sp.get('name')}: bad traceId")
                if not is_hex(sp.get("spanId", ""), 16):
                    problems.append(f"{sp.get('name')}: bad spanId")
                if "parentSpanId" in sp and not is_hex(sp["parentSpanId"], 16):
                    problems.append(f"{sp.get('name')}: bad parentSpanId")
                if sp.get("kind") not in KIND.values():
                    problems.append(f"{sp.get('name')}: bad kind")
                if int(sp["endTimeUnixNano"]) < int(sp["startTimeUnixNano"]):
                    problems.append(f"{sp.get('name')}: ends before it starts")
    if not doc.get("resourceSpans"):
        problems.append("no resourceSpans")
    return problems


def dumps(doc):
    return json.dumps(doc, separators=(",", ":"), sort_keys=True)

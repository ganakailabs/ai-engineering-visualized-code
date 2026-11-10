"""Implementation tests for Chapter 3: span tree, export, completeness, redaction."""
import _path  # noqa: F401

import copy
import re
import tempfile
from pathlib import Path

import ch03
import logsink
import trace

tr = trace.Tracer()
api, job = ch03.one_ticket(tr, trace.T0_NS)
assert job["trace_id"] == api["trace_id"] and job["parent_id"] == api["span_id"]
assert re.fullmatch(r"00-[0-9a-f]{32}-[0-9a-f]{16}-01", trace.traceparent(api))
names = {s["name"]: s for s in tr.spans}
step = names["invoke_agent northwind-assistant"]
for child in ("retrieval", "chat stub", "execute_tool issue_refund"):
    assert names[child]["parent_id"] == step["span_id"]
    assert names[child]["start_ns"] >= step["start_ns"]
    assert names[child]["end_ns"] <= step["end_ns"]
assert step["end_ns"] <= job["end_ns"]
assert names["chat stub"]["attrs"]["gen_ai.operation.name"] == "chat"
assert not any("?" in line for line in trace.tree(tr.spans, api["trace_id"]))

# export: OTLP/JSON shape, and the check catches a broken document
doc = trace.to_otlp(tr.spans)
assert trace.check_otlp(doc) == []
spans = [s for rs in doc["resourceSpans"] for ss in rs["scopeSpans"] for s in ss["spans"]]
assert len(spans) == 6 and {s["kind"] for s in spans} == {1, 2, 3, 5}
bad = copy.deepcopy(doc)
bad["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["spanId"] = "XYZ"
assert trace.check_otlp(bad)

# completeness: dropped worker spans are counted, and the metric is withheld
spans, jobs = ch03.tuesday()
received = [s for s in spans if s["name"] == "process tickets"]
assert (jobs, len(received)) == (30, 20)
assert len(received) / jobs < ch03.FLOOR

# an orphan shows up when a parent never arrives
orphan = trace.Tracer(9)
o = orphan.start("process tickets", "CONSUMER", parent="00-" + "a" * 32 + "-" + "b" * 16 + "-01")
assert any(line.startswith("?") for line in trace.tree(orphan.spans, o["trace_id"]))

# logs: the redacting sink leaves nothing for the scan to find
tmp = Path(tempfile.mkdtemp())
rec = {"customer": "Asha Rao", "note": "call +91 98765 43210 or asha.rao@example.com",
       "ticket_text": "Asha here, my mug set is chipped"}
raw = logsink.Sink(tmp / "raw.log", redacting=False)
raw.write(rec)
assert len(logsink.scan(raw.path)) >= 4
sink = logsink.Sink(tmp / "app.log")
sink.write(rec)
assert logsink.scan(sink.path) == []
assert "ticket_text" not in open(sink.path).read()
# W3C traceparent validation: malformed or all-zero context restarts the trace
good = "00-" + "ab" * 16 + "-" + "cd" * 8 + "-01"
assert trace.parse_traceparent(good) == ("ab" * 16, "cd" * 8)
for bad in ("", "00-hello-world-01", "00-" + "0" * 32 + "-" + "cd" * 8 + "-01",
            "00-" + "ab" * 16 + "-" + "0" * 16 + "-01", "ff-" + "ab" * 16 + "-" + "cd" * 8 + "-01",
            "00-" + "AB" * 16 + "-" + "cd" * 8 + "-01"):
    assert trace.parse_traceparent(bad) is None, bad
    sp = trace.Tracer(seed=1).start("x", parent=bad)
    assert sp["parent_id"] == "" and sp["attrs"]["trace.restarted"] and set(sp["trace_id"]) != {"0"}
joined = trace.Tracer(seed=1).start("x", parent=good)
assert joined["trace_id"] == "ab" * 16 and "trace.restarted" not in joined["attrs"]
# the sink's patterns are fixture-sized: an address passes through unmasked
import json as _json, tempfile as _tf
from pathlib import Path as _P
import logsink
sk = logsink.Sink(_P(_tf.mkdtemp()) / "a.log")
assert "Lake Road" in _json.loads(sk.write({"note": "flat 4B, 12 Lake Road"}))["note"]
assert logsink.scan(sk.path) == []          # the scan cannot see what it has no pattern for
print("test_trace: OK")

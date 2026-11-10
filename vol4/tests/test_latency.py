"""Implementation tests for Chapter 7: schedule, critical path, skip, stream."""
import _path  # noqa: F401

import latency as L

# a hand-built DAG: a -> (b 100 | c 30) -> d
steps = {"a": (10, []), "b": (100, ["a"]), "c": (30, ["a"]), "d": (5, ["b", "c"])}
model = {"ttft_ms": 0, "reply_tokens": 0, "tokens_per_s": 1}
start, end = L.schedule(steps, model)
assert end["d"] == 115 and start["d"] == 110
spans = L.to_spans(start, end)
assert L.critical_path(spans) == ["a", "b", "d"]
assert L.total_ms(spans) == 115

# speeding up the off-path box changes nothing; slowing it past its slack does
assert L.schedule(steps, model, {"c": {"ms": 1}})[1]["d"] == 115
s2, e2 = L.schedule(steps, model, {"c": {"ms": 150}})
assert e2["d"] == 165 and L.critical_path(L.to_spans(s2, e2)) == ["a", "c", "d"]

# skip removes the step and rewires its users to its dependencies
s3, e3 = L.schedule(steps, model, {"b": None})
assert "b" not in e3 and e3["d"] == 45

# streaming moves the first words, never the total
start, end = L.schedule(L.STEPS)
assert L.first_words_ms(start) is None
assert L.first_words_ms(start, streaming=True) == start["generate"] + L.MODEL["ttft_ms"]
assert L.gen_ms(L.MODEL) == 600 + 1400
# slack from the dependency edges: the retrieval branch has 150 ms to spare
st, en = L.schedule(L.STEPS)
sl = L.slack(L.STEPS, st, en)
assert sl["retrieve"] == sl["rerank"] == 150
assert all(sl[n] == 0 for n in ("receive", "check_input", "triage", "order_lookup",
                                "generate", "check_output", "send"))
assert (st["generate"], en["generate"], en["send"]) == (850, 2850, 2920)
# tied end times: the timestamp walk picks the unrelated sibling, the edges do not
import ch07
t, e = ch07.tied_ends()
assert "audit" in t and "audit" not in e and "lookup" in e
print("test_latency: OK")

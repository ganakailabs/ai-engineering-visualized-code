"""Chapter 7: latency engineering on the critical path.

MM-125 Critical Path Waterfall: in a span tree, total time is set by the chain of
       spans that finish last; in this fixed schedule, with no shared resources,
       speeding up a span off that chain does not change this request's total.
MM-126 Stream, Parallelize, Skip: the three moves that shorten what the customer
       waits for. Streaming changes when the first words show, not the total.

Teaching choices, said out loud:
- the pipeline is a small DAG of steps with simulated durations in milliseconds
  (the book's numbers, not measurements); spans come from Chapter 3's Tracer;
- generation is split into time to first token (TTFT) and decoding, where
  decoding = reply tokens / tokens per second.
"""
import trace as T

# The warranty ticket (SC-015: "my NW-500 battery stopped charging"), simulated ms.
# step: (duration_ms, depends_on)
STEPS = {
    "receive":      (15, []),
    "check_input":  (35, ["receive"]),
    "triage":       (280, ["check_input"]),
    "order_lookup": (520, ["triage"]),
    "retrieve":     (250, ["triage"]),
    "rerank":       (120, ["retrieve"]),
    "generate":     (None, ["order_lookup", "rerank"]),     # TTFT + decode, below
    "check_output": (60, ["generate"]),
    "send":         (10, ["check_output"]),
}
MODEL = {"ttft_ms": 600, "reply_tokens": 280, "tokens_per_s": 200}


def gen_ms(model):
    return model["ttft_ms"] + 1000 * model["reply_tokens"] / model["tokens_per_s"]


def schedule(steps, model=MODEL, overrides=None):
    """Earliest start for each step = latest end of its dependencies."""
    steps = {k: (v[0], list(v[1])) for k, v in steps.items()}
    for name, change in (overrides or {}).items():
        if change is None:                       # skip: drop the step, rewire its users
            dur, deps = steps.pop(name)
            for k, (d, ds) in steps.items():
                if name in ds:
                    steps[k] = (d, [x for x in ds if x != name] +
                                [x for x in deps if x not in ds])
        else:
            dur, deps = steps[name]
            steps[name] = (change.get("ms", dur), change.get("deps", deps))
    start, end = {}, {}
    while len(end) < len(steps):
        for name, (dur, deps) in steps.items():
            if name not in end and all(d in end for d in deps):
                start[name] = max((end[d] for d in deps), default=0.0)
                end[name] = start[name] + (gen_ms(model) if dur is None else dur)
    return start, end


def to_spans(start, end, seed=7):
    tr = T.Tracer(seed)
    root = tr.start("ticket T-1501-a", kind="SERVER", service="api")
    T.Tracer.end(root, max(end.values()))
    for name in sorted(start, key=lambda n: (start[n], n)):
        sp = tr.start(name, parent=root, start_ns=T.T0_NS + int(start[name] * 1e6))
        T.Tracer.end(sp, end[name] - start[name])
    return tr.spans


def critical_path(spans):
    """Walk back from the root's end: take the child that ends last, then the child that
    ends last before that one started, and so on. Returns names, earliest first.
    ASSUMES a flat fixture: every child of the root is a step of one pipeline and a
    step that ends exactly when another starts is its dependency. Timestamps are not
    causality: with tied end times it can pick an unrelated sibling. When you have
    the scheduler's dependency edges, use slack() instead."""
    root = next(s for s in spans if not s["parent_id"])
    kids = [s for s in spans if s["parent_id"] == root["span_id"]]
    path, cursor = [], root["end_ns"]
    while True:
        done = [s for s in kids if s["end_ns"] <= cursor and s not in path]
        if not done:
            break
        last = max(done, key=lambda s: (s["end_ns"], s["end_ns"] - s["start_ns"]))
        path.append(last)
        cursor = last["start_ns"]
    return [s["name"] for s in reversed(path)]


def slack(steps, start, end):
    """Slack per step from the dependency edges: how late it could finish without
    delaying the end. Zero slack = on the critical path (ties give several paths)."""
    total = max(end.values())
    users = {n: [k for k, (_, deps) in steps.items() if n in deps] for n in steps}
    latest = {}
    for n in sorted(end, key=lambda n: -end[n]):          # sinks first
        latest[n] = min((latest[u] - (end[u] - start[u]) for u in users[n]), default=total)
    return {n: round(latest[n] - end[n], 3) for n in end}


def total_ms(spans):
    root = next(s for s in spans if not s["parent_id"])
    return (root["end_ns"] - root["start_ns"]) / 1e6


def waterfall(spans, width=30, on=()):
    """One bar per span on a shared time axis; '#' marks the critical path."""
    root = next(s for s in spans if not s["parent_id"])
    scale = width / (root["end_ns"] - root["start_ns"])
    lines = []
    for s in sorted((s for s in spans if s["parent_id"]), key=lambda s: s["start_ns"]):
        a = int((s["start_ns"] - root["start_ns"]) * scale)
        b = max(a + 1, int((s["end_ns"] - root["start_ns"]) * scale))
        bar = (" " * a + ("#" if s["name"] in on else "=") * (b - a)).ljust(width)
        ms = (s["end_ns"] - s["start_ns"]) / 1e6
        lines.append(f"{s['name']:<13}|{bar}| {ms:>5.0f} ms")
    return lines


def first_words_ms(start, model=MODEL, streaming=False):
    """What the customer waits for before any reply text shows."""
    if not streaming:
        return None
    return start["generate"] + model["ttft_ms"]

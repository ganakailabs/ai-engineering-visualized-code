"""Chapter 7: Latency Engineering: The Critical Path.

Run from the repo root:  python3 vol4/ch07.py
Part 1 draws the waterfall of one warranty ticket (SC-015) from Chapter 3's spans and
marks the critical path. Part 2 speeds up the reranker, which is not on that path, and
the total does not move. Part 3 applies the three moves: parallelize, skip, stream.
Part 4 (sidebar) compares time to first token with tokens per second. All durations
are simulated; none is a measurement of a real model or service.
"""
import _root  # noqa: F401

import latency as L


def show(path, head="critical: "):
    """The path, wrapped to fit a printed page."""
    line, out = head, []
    for i, name in enumerate(path):
        piece = name if i == 0 else " > " + name
        if len(line) + len(piece) > 66:
            out.append(line)
            line = " " * (len(head) - 2) + piece
        else:
            line += piece
    return "\n".join(out + [line])


def run(overrides=None, model=L.MODEL):
    start, end = L.schedule(L.STEPS, model, overrides)
    spans = L.to_spans(start, end)
    return start, spans, L.critical_path(spans)


def tied_ends():
    """A synthetic counterexample for the timestamp walk: 'audit' and 'lookup' both
    end at 100 ms, but only 'lookup' feeds 'generate'. The walk picks by end time
    (then by duration), so it chooses the unrelated sibling; the edges do not."""
    steps = {"audit": (100, []), "fetch": (50, []), "lookup": (50, ["fetch"]),
             "generate": (100, ["lookup"])}
    st, en = L.schedule(steps)
    by_time = L.critical_path(L.to_spans(st, en))
    sl = L.slack(steps, st, en)
    by_edges = [n for n in sorted(st, key=lambda n: (st[n], n)) if sl[n] == 0]
    return [f"timestamps: {' > '.join(by_time)}", f"edges:      {' > '.join(by_edges)}"]


PARALLEL = {"order_lookup": {"deps": ["check_input"]}}   # the order id is in the ticket
SKIP = dict(PARALLEL, triage=None)                         # the form already says "warranty"

if __name__ == "__main__":
    print("== Part 1: the critical path (MM-125) ==")
    start, spans, path = run()
    print("ticket T-1501-a (SC-015, warranty), simulated durations")
    print("\n".join(L.waterfall(spans, on=path)))
    print(f"total={L.total_ms(spans):.0f} ms")
    print(show(path))
    st0, en0 = L.schedule(L.STEPS)
    sl = L.slack(L.STEPS, st0, en0)
    print("slack from dependency edges: " + ", ".join(
        f"{n} {sl[n]:.0f} ms" for n in ("retrieve", "rerank")) + "; path steps 0 ms")
    print("tied ends (timestamps vs edges):")
    for line in tied_ends():
        print("  " + line)

    print("\n== Part 2: speeding up the wrong box ==")
    _, fast, fpath = run({"rerank": {"ms": 40}})
    print(f"rerank 120 -> 40 ms: total={L.total_ms(fast):.0f} ms "
          f"(was {L.total_ms(spans):.0f}); rerank on path: {'rerank' in fpath}")

    print("\n== Part 3: stream, parallelize, skip (MM-126) ==")
    rows = [("baseline", None, False), ("parallelize lookup", PARALLEL, False),
            ("+ skip triage", SKIP, False), ("+ stream", SKIP, True)]
    for label, ov, streaming in rows:
        st, sp, p = run(ov)
        first = L.first_words_ms(st, streaming=streaming)
        shown = f"{first:.0f}" if first else f"{L.total_ms(sp):.0f}"
        print(f"{label:<19} total={L.total_ms(sp):>4.0f} ms  first words={shown:>4} ms")
    st, sp, p = run(SKIP)
    print(show(p, "critical now: "))

    print("\n== Sidebar: TTFT vs tokens per second (simulated models) ==")
    models = {"quick-start": {"ttft_ms": 300, "tokens_per_s": 60},
              "fast-decode": {"ttft_ms": 900, "tokens_per_s": 200}}
    for tokens in (20, 280):
        cells = []
        for name, m in models.items():
            ms = L.gen_ms(dict(m, reply_tokens=tokens))
            cells.append(f"{name}={ms:.0f} ms")
        print(f"reply {tokens:>3} tokens: {'  '.join(cells)}")

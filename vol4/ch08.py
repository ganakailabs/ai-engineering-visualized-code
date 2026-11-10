"""Chapter 8: Streaming, Cancellation and Backpressure.

Run from the repo root:  python3 vol4/ch08.py
Part 1 streams the risky draft the naive way and under the stream contract (MM-164).
Part 2 drops the connection and resumes from the last event id, then cancels a job.
Part 3 sizes the workers for the simulated peak and sends twice the peak to an unbounded
and a bounded queue (MM-165). The model is the stub; every arrival and duration is simulated.
"""
import textwrap

import _root  # noqa: F401

import stream as S

PEAK_PER_MIN, SERVICE_S, DEADLINE_S, MAX_UTIL = 30, 12, 60, 0.75   # simulated lab numbers

if __name__ == "__main__":
    print("== Part 1: the stream contract (MM-164), order #3100 ==")
    s, ok, clause = S.naive_stream("3100")
    shown = " ".join(e["data"] for e in s.events if e["event"] == "partial")
    print("naive: customer saw")
    print(textwrap.fill(f'"{shown}"', 66, initial_indent="  ", subsequent_indent="  "))
    print(f"naive: check output ok={ok} clause={clause}  <- after it was shown")
    s, ok, clause = S.contract_stream("3100")
    for e in s.events:
        line = f'stream event={e["event"]} id={e["id"]} "{e["data"]}"'
        if len(line) > 66:
            line = f'stream event={e["event"]} id={e["id"]}\n' + textwrap.fill(
                f'"{e["data"]}"', 66, initial_indent="  ", subsequent_indent="  ")
        print(line)
    print(f"decision text before final: {len(S.decision_before_final(s))}")
    leak = ("Your order #2001 left our warehouse and goes to " + S.ADDRESSES["c-42"]
            + " tomorrow.")
    d, ok, clause = S.delivery_stream("2001", leak)
    early = [e["data"] for e in d.events if e["event"] != "final"]
    print(f"delivery draft for #2001 names c-42's address -> check ok={ok} ({clause})"
          f"\n  streamed before the check: status lines only "
          f"({all(x in S.NEUTRAL.values() or x == '' for x in early)})")
    print("wire format of event 2:")
    print(S.sse(s.events[1]), end="")

    print("== Part 2: reconnect and cancel ==")
    seen = s.events[:3]
    resumed = s.since(seen[-1]["id"])
    print(f"client reconnect last_event={seen[-1]['id']} -> resume ids "
          f"{[e['id'] for e in resumed]}")
    for after in ("decide", "pay"):
        print(f"client cancel after {after} -> ran {' '.join(S.run_with_cancel(after))}")

    print("== Part 3: backpressure (MM-165), simulated ==")
    busy, workers = S.workers_needed(PEAK_PER_MIN, SERVICE_S, MAX_UTIL)
    print(f"sizing: peak {PEAK_PER_MIN}/min x {SERVICE_S} s = {busy:.1f} busy workers; "
          f"at {MAX_UTIL:.0%} -> {workers} workers")
    print(f"queue limit: {S.queue_limit(workers, SERVICE_S, DEADLINE_S)} waiting "
          f"(first checked reply within {DEADLINE_S} s)")
    print(f"twice the peak ({2 * PEAK_PER_MIN}/min) for 10 min:")
    for bounded in (False, True):
        out, done = S.simulate(2 * PEAK_PER_MIN, 10, workers, SERVICE_S, DEADLINE_S, bounded)
        adm = [o for o in out.values() if o["admitted"]]
        late = sum(1 for o in adm if o["reply_s"] > DEADLINE_S)
        worst = max(o["reply_s"] for o in adm)
        print(f"{'bounded  ' if bounded else 'unbounded'} admitted={len(adm)}/{len(out)} "
              f"refused={len(out) - len(adm)} late={late} worst={worst} s")
    refused = next(t for t, o in out.items() if not o["admitted"])
    print(f"admit {refused} queue=full -> 503 retry_after={out[refused]['retry_after_s']}")
    on_time = sum(1 for o in adm if o["reply_s"] <= DEADLINE_S)
    print(f"bounded: admission {len(adm)}/{len(out)} = {len(adm) / len(out):.0%}, "
          f"on time {on_time}/{len(adm)} admitted = {on_time / len(adm):.0%}")
    print(f"  on time out of all demand {on_time}/{len(out)} = {on_time / len(out):.0%}")
    out, _ = S.simulate(2 * PEAK_PER_MIN, 10, workers, SERVICE_S, DEADLINE_S, True,
                        tail=(10, 48))
    adm = [o for o in out.values() if o["admitted"]]
    late = sum(1 for o in adm if o["reply_s"] > DEADLINE_S)
    print(f"long tail (1 in 10 takes 48 s), same limit: admitted={len(adm)}/{len(out)}"
          f"\n  late={late} worst={max(o['reply_s'] for o in adm)} s")

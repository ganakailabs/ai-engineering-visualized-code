"""Chapter 2: SLOs and Error Budgets.

Run from the repo root:  python3 vol4/ch02.py
Reads vol4/slo.json, replays a seeded simulated week (vol4/traffic.py) and prints the
event accounting, the latency error budget day by day, the release policy's answers
and a safety invariant that no budget can absorb. All numbers are simulated.
"""
import _root  # noqa: F401

import slo
import traffic

if __name__ == "__main__":
    card, week = slo.load(), traffic.week()
    lat = card["slos"]["latency"]
    print("== The SLO card (MM-118) ==")
    probes = sum(t["tenant_id"] == "probe" for t in week)
    cancelled = sum(t["cancelled"] and t["tenant_id"] != "probe" for t in week)
    print(f"slo latency owner={lat['owner']} good = first checked reply "
          f"<= {lat['threshold_s']}s from creation")
    print(f"  window {card['window_days']} days: {len(week)} tickets, excluded "
          f"{probes} probe + {cancelled} cancelled (simulated)")
    print(f"admission created={len(week)} of attempted={len(week)} "
          f"(simulated: nothing refused)")
    print(f"slo quality owner={card['slos']['quality']['owner']}: "
          f"{card['slos']['quality']['status']}")
    limit = card["cost_limit"]["max_tokens_per_ticket"]
    print(f"cost limit {limit} tokens/ticket: over={len(slo.cost_over(week, limit))} "
          f"(simulated)")
    print(f"invariant pii_in_reply violations={len(slo.invariant_violations(week))}")

    print("\n== The error budget (MM-162) ==")
    b = slo.latency(week, lat)
    seen, by_day = [], []
    for day in traffic.DAYS:
        seen += [t for t in week if t["day"] == day]
        by_day.append(f"{day} {slo.latency(seen, lat)['bad']}")
    print(f"bad so far: {', '.join(by_day)} (allowed {b['allowed_bad']})")
    rates = []
    for day in traffic.DAYS:
        d = slo.latency([t for t in week if t["day"] == day], lat)
        r = slo.burn_rate(d["bad"], d["eligible"], lat["target_permille"])
        rates.append(f"{day} {r:.1f}" if r else f"{day} 0")
    print(f"burn rate: {', '.join(rates)}")
    print(f"slo latency eligible={b['eligible']} good={b['good']} "
          f"target={lat['target_permille'] / 10:.1f}%")
    print(f"  allowed_bad={b['allowed_bad']} used={b['bad']} (simulated)")
    for name, kind in (("prompt-v2", "prompt"), ("rollback-to-v1", "rollback")):
        ok, why = slo.release_allowed(kind, {"latency": b}, [])
        print(f"policy {name} ({kind}) -> {'allowed' if ok else 'blocked'}: {why}")

    print("\n== Safety is not budgeted ==")
    leaked = [dict(t) for t in week]
    leaked[100]["reply"] += " Questions? Write to asha.rao@example.com."
    v = slo.invariant_violations(leaked)
    print(f"invariant pii_in_reply violations={len(v)} ({v[0]}) -> incident")
    ok, why = slo.release_allowed("prompt", {"latency": dict(b, spent=False)}, v)
    print(f"policy prompt-v2 (budget left) -> {'allowed' if ok else 'blocked'}: {why}")

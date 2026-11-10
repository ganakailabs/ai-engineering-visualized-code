"""Chapter 9: Cost Engineering: Tokens and Caching.

Run from the repo root:  python3 vol4/ch09.py
Part 1 prices one ticket and compares two releases per call and per resolved ticket
(MM-127). Part 2 runs the application caches, naive and checked (MM-128). Part 3 checks
the prompt layout for a stable prefix (MM-176). Prices are made-up units ("u"); the
ticket mix is simulated; the stub model has no provider usage report.
"""
import _root  # noqa: F401

import cost as C

T1 = {"ticket_id": "T-2001-a", "at": "2026-10-04 10:02", "order_id": "2001",
      "text": "My mug set arrived cracked. Can I get a refund?"}
T2 = {"ticket_id": "T-3100-a", "at": "2026-10-04 10:05", "order_id": "3100",
      "text": "Can I return my headphones?"}

if __name__ == "__main__":
    print("== Part 1: cost per resolved ticket (MM-127) ==")
    ts = C.tickets("small")
    t = next(x for x in ts if x["escalated"] and x["calls"] > 1)
    r = C.ticket_cost(t)
    print(f"cost ticket={t['id']} total={sum(r.values()):.1f} "
          f"resolved={'yes' if t['resolved'] else 'no'} (simulated units)")
    print("  " + " ".join(f"{k}={v:.1f}" for k, v in r.items()))
    for rel in ("big", "small"):
        ts = C.tickets(rel)
        print(f"release {rel:5} per call={C.per_call(ts):.2f}  "
              f"per resolved={C.per_resolved(ts):.2f}  "
              f"escalated={sum(x['escalated'] for x in ts)}/{len(ts)}")
    for kind in C.TYPES:
        row = [C.per_resolved([x for x in C.tickets(rel) if x["type"] == kind])
               for rel in ("big", "small")]
        print(f"  {kind:9} per resolved: big={row[0]:.2f} small={row[1]:.2f}")

    print("== Part 2: the application caches (MM-128) ==")
    q1 = "Can I get a refund for order #2001? It arrived cracked."
    q2 = "Can I get a refund for order #3100? It arrived cracked."
    faq = "How long does delivery usually take?"
    refund = "Refund of INR 950 for order #2001 is on its way (R2)."
    for name, kw in (("naive", dict(entity=False, structured=False)),
                     ("entity check", dict(entity=True, structured=False))):
        cache = C.AppCache("2026-09-15", "idx-7", **kw)
        cache.put(q1, refund)
        reply, why = cache.get(q2)
        print(f"{name}: get #3100 -> {why}")
        if reply:
            print(f'  served: "{reply}"')
    vague = "Please refund the order we discussed."
    personal = dict(C.GENERAL, route="refund", context=True, sources=["order", "handbook"])
    print(f'text rule on "{vague}"\n  -> personal={C.text_rule(vague)} (no order id in the text)')
    cache = C.AppCache("2026-09-15", "idx-7")
    print(f"structured: put it -> {cache.put(vague, refund, personal)}")
    used_order = dict(C.GENERAL, context=True, sources=["handbook", "order"])
    print(f"structured: faq reply that read the order\n  -> "
          f"{cache.put('Where is my parcel?', 'It left Pune today.', used_order)}")
    print(f"put faq -> {cache.put(faq, 'Orders usually arrive within 5 business days (S1).')}")
    print(f"get faq -> {cache.get(faq)[1]}")
    print(f"get faq reworded -> {cache.get('How many days does delivery usually take?')[1]}")
    print(f"get faq tenant=b -> {cache.get(faq, dict(C.GENERAL, tenant='b'))[1]}")
    print(f"get faq permissions v2 -> {cache.get(faq, dict(C.GENERAL, perm_v=2))[1]}")
    print(f"get faq handbook access revoked -> "
          f"{cache.get(faq, dict(C.GENERAL, can_read=set()))[1]}")
    dropped = cache.set_versions("2026-11-01", "idx-7")
    print(f"app_cache flushed policy=2026-11-01 dropped={dropped}")
    print(f"get faq -> {cache.get(faq)[1]}")

    print("== Part 3: stable first, changing last (MM-176) ==")
    for name, layout in (("as shipped", C.AS_SHIPPED), ("stable first", C.STABLE_FIRST)):
        shared = C.shared_prefix_tokens(C.prompt(T1, layout), C.prompt(T2, layout))
        print(f"{name}: {' > '.join(layout)}")
        print(f"  shared prefix={shared} of {C.stable_tokens(T1)} stable tokens"
              f" -> {'pass' if C.prefix_stable(T1, T2, layout) else 'FAIL'}")
    old = C.prompt(T1, C.STABLE_FIRST)
    new = C.prompt(T1, C.STABLE_FIRST, policy_version="2026-11-01")
    print(f"policy 2026-09-15 -> 2026-11-01: shared prefix="
          f"{C.shared_prefix_tokens(old, new)} of {C.stable_tokens(T1)}")
    print("provider_cache: unmeasured; read it from the provider's usage report;")
    print("  the stub has none, so no hit rate or saving is printed")

"""Chapter 14: Index Lifecycle: Updates, Deletes, Rebuilds and Drift.

Run from the repo root:  python3 vol3/ch14.py
Monday a clause changes; Tuesday a page is restricted to agents without a text change.
sync() catches both, each on its own hash. Then build, check, switch: a half-built
index and a mixed-embedder index are refused; a complete one that passes the held-out
set is switched in. No model is used.
"""
import _root  # noqa: F401

import lifecycle as L

if __name__ == "__main__":
    src = L.sources()
    live = L.build(src, "INDEX v1", "gram-v1")

    print("Part 1 (MM-089): the stale index")
    src["ret-30"].update(text="unused items refund within 14 days original packaging", version=2)
    src["nw550-batt"].update(audience="internal", version=2)        # text unchanged
    print(f"  break  content-hash-only sync sees changed={L.content_only_sync(src, live)} of 2 changes")
    print(f"  before {L.check(src, live)}")
    s = L.sync(src, live)
    print(f"  sync changed={s['changed']} access_changed={s['access_changed']} removed={s['removed']}")
    c = L.check(src, live)
    print(f"  check  index consistent={'yes' if not (c['stale'] or c['missing']) else 'no'} "
          f"orphans={c['orphans']}")
    hit = live.search("refund window for unused items")[0]
    print(f"  answer source={hit} source_version={live.rows[hit]['version']}")
    print(f"  customer search 'NW-550 battery replacement' top={live.search('NW-550 battery replacement')}")

    del src["acct-pw"]
    print(f"  delete acct-pw -> sync removed={L.sync(src, live)['removed']} "
          f"tombstones={sorted(live.tombstones)}")

    print("\nPart 2 (MM-152): build, check, switch")
    half = L.build({i: src[i] for i in list(src)[:6]}, "INDEX v2", "gram-v2")
    print(f"  half-built  {L.switch(live, half, src)[1]}")
    mixed = L.build(src, "INDEX v2", "gram-v2")
    mixed.rows["ret-30"] = dict(live.rows["ret-30"])                # one v1 vector left in
    print(f"  mixed       {L.switch(live, mixed, src)[1]}")
    full = L.build(src, "INDEX v2", "gram-v2")
    live2, why = L.switch(live, full, src)
    print(f"  complete    {why} -> live={live2.name}")

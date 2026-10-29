"""Chapter 14 exercise: change only who may see it.

Restrict one manual page to agents without changing its text, and re-sync.
Predict first: does a content-hash sync notice? No; the access hash does.
"""
import _path  # noqa: F401

import lifecycle as L

src = L.sources()
ix = L.build(src, "INDEX v1", "gram-v1")
src["nw500-pair"].update(audience="internal", version=2)
assert L.content_only_sync(src, ix) == 0
s = L.sync(src, ix)
assert s == dict(changed=0, access_changed=1, version_changed=0, added=0, removed=0, unlisted=0)
hits = ix.search("NW-500 headphones bluetooth pairing steps", audience="customer", k=3)
assert "nw500-pair" not in hits
assert "nw500-pair" in ix.search("NW-500 headphones bluetooth pairing steps", audience="internal")
print(f"sync {s}  customer top-3={hits}")
print("ch14 solution: OK")

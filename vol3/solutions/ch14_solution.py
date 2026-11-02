"""Chapter 14 exercise: change only who may see it.

Restrict one manual page to agents without changing its text, and re-sync.
Predict first: does a content-hash sync notice? No; the access hash does.

Part 2: three more events. Predict what sync() reports for each, then run it:
  a. a version bump with identical text and audience,
  b. a partial listing (the source returned only 6 documents),
  c. the next complete listing after it.
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

src = L.sources()
ix = L.build(src, "INDEX v1", "gram-v1")
src["ret-30"]["version"] = 2                                       # a. version only
s = L.sync(src, ix)
assert (s["version_changed"], s["changed"], s["access_changed"]) == (1, 0, 0)
print(f"a. version bump: {s}")
partial = dict(list(src.items())[:6])                               # b. partial listing
s = L.sync(partial, ix, complete=False)
assert s["removed"] == 0 and s["unlisted"] == len(src) - 6 and not ix.tombstones
print(f"b. partial listing: {s}")
s = L.sync(src, ix)                                                 # c. complete again
assert s["removed"] == 0
print(f"c. complete listing: {s}")
print("ch14 solution: OK")

"""Chapter 5 exercise: revoke and re-ask.

Ask once (so the answer is cached), revoke one document from tenant A, then ask again.
List every place a chunk can come back from and assert it is gone from each one:
search, parent expansion, the cache and a citation.
"""
import _path  # noqa: F401

import access as A

ASHA = A.Session("a", "asha", "customer", "IN")
Q = "damaged refund photo"
ix = A.Index()
first = A.retrieve(ix, ASHA, Q)
assert first == ["a-ret.1", "a-ret.2"]

gone = ix.revoke("a-ret")
assert ix.search(ASHA, Q) == []                                   # search
assert not set(ix.expand(ASHA, "a-ret.1")) & gone                 # parent expansion
assert ix.cached_answer(ASHA, Q) is None                          # cache
assert not ix.cite_ok(ASHA, ["a-ret.2"])                          # citation
assert A.retrieve(ix, ASHA, Q) == []
print(f"revoked={sorted(gone)} hits=0 parent=0 cache=0 cite=refused")
print("ch05 solution: OK")

"""Chapter 5: Knowledge Access: Permissions, Tenants and Poisoned Documents.

Run from the repo root:  python3 vol3/ch05.py
Two fictional storefronts share one index. No model is used.
"""
import _root  # noqa: F401

import access as A

ASHA = A.Session("a", "asha", "customer", "IN")
Q = "damaged refund photo"

if __name__ == "__main__":
    print("Part 1 (MM-090 Break): filtered search, unfiltered parent expansion")
    ix = A.Index()
    hits = ix.search(ASHA, Q)
    leak = sorted({c for h in hits for c in ix.expand(ASHA, h, filtered=False)})
    print(f"  search={hits}")
    print(f"  expanded={leak}")

    print("\nPart 2 (MM-090 Fix): the same filter at every door")
    t = A.trace()
    ids = A.retrieve(ix, ASHA, Q, t)
    print(f"  context={ids}  cite b-note.1 ok={ix.cite_ok(ASHA, ['b-note.1'])}")
    ix.revoke("a-ret", t)
    print(f"  next query hits={len(A.retrieve(ix, ASHA, Q))}")

    print("\nPart 3 (MM-153): supplier pages at ingestion")
    ix.ingest_supplier(t=t)
    print(f"  quarantine={ix.quarantine}  indexed={'sup-2' in ix.rows}")

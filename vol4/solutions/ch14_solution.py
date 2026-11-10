"""Chapter 14 exercise: Find all of Asha.

Handle "send me my data", then "delete it", then restore last night's backup. Predict
first: how many systems hold her data after the restore? None of the live stores, as
long as the restore replays the deletion journal. The backup itself still holds her
until it expires; that is why the journal exists. Stores are the simulated fixture.
"""
import _path  # noqa: F401

import privacy as P

stores = P.fixture()
nightly = P.backup(stores)
ex = P.export(stores, "asha")
print("export: " + " ".join(f"{s}={n}" for s, n in ex.items()))
print("  also listed: audit, journal (ids kept by policy)")
print("  provider (per product, dated), backups (by date)")
assert set(ex) == set(P.LIVE) and all(ex[s] for s in ("index", "memory"))

journal = []
P.delete(stores, "asha", journal)
after = sum(P.export(stores, "asha").values())
print(f"after delete: live stores holding asha={after}")
restored = P.restore(nightly, journal)
again = sum(P.export(restored, "asha").values())
print(f"after restore + journal: live stores holding asha={again}")
print(f"backup still holds asha until expiry: "
      f"{'yes' if P.present(nightly, 'asha') else 'no'}")
assert after == 0 and again == 0
print("ch14 solution: OK")

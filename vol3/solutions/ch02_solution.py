"""Chapter 2 exercise: fail halfway, at file 3 this time, then rerun.

Crash the run while the last manual is being ingested. The rerun must skip the two
files that finished, retry the one that failed, and end with exactly the ids of a
clean run: no duplicates and no orphans. Then do the same with the naive pipeline and
count its duplicates.
"""
import _path  # noqa: F401

import ingest as I

FILES = sorted(I.MANUALS.glob("*.txt"))
clean = I.Store()
I.ingest(FILES, clean, echo=False)

store = I.Store()
try:
    I.ingest(FILES, store, crash_on=3, echo=False)
    raise AssertionError("expected a crash on file 3")
except I.Crash:
    pass
assert len(store.chunks) == 8, len(store.chunks)          # files 1 and 2 committed
r = I.ingest(FILES, store, echo=False)
assert (r["skipped"], r["retried"], r["new"]) == (2, 1, 0), r
assert sorted(store.chunks) == sorted(clean.chunks)
assert I.duplicates(list(store.chunks.values())) == 0 and I.orphans(store) == []

naive = I.NaiveStore()
try:
    I.naive_ingest(FILES, naive, crash_on=3)
except I.Crash:
    pass
I.naive_ingest(FILES, naive)
dup = I.duplicates(naive.rows)
assert dup == 8 + 2, dup                                   # files 1-2 again + half of file 3
print(f"fixed: skipped={r['skipped']} retried={r['retried']} n={len(store.chunks)} duplicates=0")
print(f"naive: rows={len(naive.rows)} duplicates={dup}")
print("ch02 solution: OK")

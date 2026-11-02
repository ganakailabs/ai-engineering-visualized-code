"""Chapter 2 exercise: fail halfway, at file 3 this time, then rerun.

Part 1. Crash the run while the last manual is being ingested. The rerun must skip the
two files that finished, retry the one that failed, and end with exactly the ids of a
clean run: no duplicates and no orphans. Then do the same with the naive pipeline and
count its duplicates.

Part 2 (a failed UPDATE). Ingest version 1, fail while version 2 of the lamp manual is
being committed, restart, check that version 1 is still the active version, retry, and
check that version 2 is now active. The manifest keeps the active version apart from
the latest attempt.
"""
import shutil
import tempfile
from pathlib import Path

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

# Part 2: a failed update must leave version 1 serving
d = Path(tempfile.mkdtemp())
for f in FILES:
    shutil.copy(f, d / f.name)
files = sorted(d.glob("*.txt"))
store = I.Store()
I.ingest(files, store, echo=False)                                  # 1. version 1 ok
v1 = dict(store.chunks)
lamp = d / "desk-lamp-dl1.txt"
lamp.write_text(lamp.read_text().replace("version: 2026-05-10", "version: 2026-10-01"))
try:
    I.ingest(files, store, crash_in_commit=1, echo=False)          # 2. version 2 fails
    raise AssertionError("expected a crash while committing version 2")
except I.Crash:
    pass
rec = store.manifest["files"][lamp.name]                            # 3. restart and look
assert rec["active"]["version"] == "2026-05-10" and rec["last_attempt"]["status"] == "failed"
assert store.chunks == v1 and I.orphans(store) == []
print(f"after the failed update: active={rec['active']['version']} "
      f"last_attempt={rec['last_attempt']['status']} chunks={len(store.chunks)} orphans=0")
r = I.ingest(files, store, echo=False)                              # 4. retry
rec = store.manifest["files"][lamp.name]                            # 5. version 2 active
assert (r["retried"], r["skipped"]) == (1, 2), r
assert rec["active"]["version"] == "2026-10-01" and rec["last_attempt"]["status"] == "ok"
assert len(store.chunks) == 12 and I.orphans(store) == []
print(f"after the retry: retried={r['retried']} skipped={r['skipped']} "
      f"active={rec['active']['version']} last_attempt={rec['last_attempt']['status']} "
      f"chunks={len(store.chunks)} orphans=0")
shutil.rmtree(d)
print("ch02 solution: OK")

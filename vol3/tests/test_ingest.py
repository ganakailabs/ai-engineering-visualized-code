"""Implementation tests for Chapter 2: stable ids, provenance and safe re-runs."""
import _path  # noqa: F401

import shutil
import tempfile
from pathlib import Path

import ingest as I

MANUALS = sorted(I.MANUALS.glob("*.txt"))
assert len(MANUALS) == 3


def fresh():
    d = Path(tempfile.mkdtemp())
    for f in MANUALS:
        shutil.copy(f, d / f.name)
    return d


# MM-148: every chunk knows its source, version and place
d = fresh()
store = I.Store()
run = I.ingest(sorted(d.glob("*.txt")), store, echo=False)
assert run["status"] == {f.name: "ok" for f in MANUALS}
ids = sorted(store.chunks)
assert len(ids) == len(set(ids)) == 12, len(ids)
c = store.chunks["man-nw500@2026-07-01:p2.b2"]
assert c["source"] == "man-nw500" and c["version"] == "2026-07-01"
assert c["page"] == 2 and c["block"] == 2 and "hold the power button for 10 seconds" in c["text"]
assert c["file"] == "nw-500-headphones.txt" and len(c["sha256"]) == 64
for ch in store.chunks.values():
    I.check_provenance(ch)                         # raises on a missing field
try:
    I.check_provenance({"id": "x", "text": "no source"})
    raise AssertionError("a chunk with no provenance was accepted")
except I.ProvenanceError:
    pass

# ids are stable: a second clean run gives the same ids
assert sorted(I.ingest(sorted(fresh().glob("*.txt")), I.Store(), echo=False)["ids"]) == ids

# MM-070 Break: random ids, chunks written as they are made, crash on file 2, full rerun
naive = I.NaiveStore()
try:
    I.naive_ingest(sorted(d.glob("*.txt")), naive, crash_on=2)
except I.Crash:
    pass
I.naive_ingest(sorted(d.glob("*.txt")), naive)
assert len(naive.rows) > 12 and I.duplicates(naive.rows) > 0

# MM-070 Fix: crash on file 2, then rerun with the manifest
store = I.Store()
try:
    I.ingest(sorted(d.glob("*.txt")), store, crash_on=2, echo=False)
    raise AssertionError("expected a crash")
except I.Crash:
    pass
assert store.manifest["files"][sorted(f.name for f in MANUALS)[1]]["status"] == "failed"
assert len({c["file"] for c in store.chunks.values()}) == 1, "file 2 left no partial chunks"
again = I.ingest(sorted(d.glob("*.txt")), store, echo=False)
assert again["skipped"] == 1 and again["retried"] == 1 and again["new"] == 1
assert sorted(store.chunks) == ids
assert I.duplicates(list(store.chunks.values())) == 0 and I.orphans(store) == []

# a new manual version replaces the old chunks in the same commit: no orphans
f = d / "desk-lamp-dl1.txt"
f.write_text(f.read_text().replace("version: 2026-05-10", "version: 2026-10-01"))
bump = I.ingest(sorted(d.glob("*.txt")), store, echo=False)
assert bump["changed"] == 1 and bump["skipped"] == 2
assert not any(k.startswith("man-dl1@2026-05-10") for k in store.chunks)
assert any(k.startswith("man-dl1@2026-10-01") for k in store.chunks)
assert len(store.chunks) == 12 and I.orphans(store) == []
# duplicates take slots in the top k a model is given
import ch02  # noqa: E402
assert ch02.top3(ch02.CHARGE, naive.rows)[:2] == ["nw-500-headphones:p1.b2"] * 2
assert len(set(ch02.top3(ch02.CHARGE, list(store.chunks.values())))) == 3
print("test_ingest: OK")

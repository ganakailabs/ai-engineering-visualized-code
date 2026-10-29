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

# Review probe: crash in the middle of staging a file's chunks. Nothing of that file
# is published; the index is exactly what it was before the run.
store = I.Store()
I.ingest(MANUALS[:1], store, echo=False)
before = dict(store.chunks)
try:
    I.ingest(MANUALS, store, crash_in_commit=2, echo=False)
    raise AssertionError("expected a crash")
except I.Crash:
    pass
assert store.chunks == before, "a mid-commit crash published a partial file"
assert store.manifest["files"][MANUALS[1].name]["status"] == "failed"
again = I.ingest(MANUALS, store, echo=False)
assert sorted(store.chunks) == ids and I.orphans(store) == []

# A changed pipeline (new chunker settings) rebuilds every file, even unchanged bytes.
store = I.Store()
I.ingest(MANUALS, store, echo=False)
same = I.ingest(MANUALS, store, echo=False)
assert same["skipped"] == 3
newer = dict(I.PIPELINE, chunker="one-block-per-chunk/2")
rebuilt = I.ingest(MANUALS, store, echo=False, pipeline=newer)
assert rebuilt["skipped"] == 0 and rebuilt["changed"] == 3
assert I.ingest(MANUALS, store, echo=False, pipeline=newer)["skipped"] == 3

# Restart in a fresh process: save (temp file + rename), crash, load, rerun.
import json  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
work = Path(tempfile.mkdtemp())
store = I.Store()
try:
    I.ingest(MANUALS, store, crash_on=3, echo=False)
except I.Crash:
    pass
store.save(work / "store.json")
assert not (work / "store.json.tmp").exists()
code = ("import sys; sys.path.insert(0, %r); import ingest as I, json; from pathlib import Path; "
        "s = I.Store.load(%r); r = I.ingest(sorted(I.MANUALS.glob('*.txt')), s, echo=False); "
        "print(json.dumps([r['skipped'], r['retried'], sorted(s.chunks), I.orphans(s)]))"
        % (str(Path(I.__file__).parent), str(work / "store.json")))
out = json.loads(subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                                check=True).stdout.strip().splitlines()[-1])
assert out[0] == 2 and out[1] == 1 and out[2] == ids and out[3] == [], out

# The manifest is keyed by file name: a renamed file is ingested again, but stable
# ids mean it replaces its chunks instead of duplicating them.
d = fresh()
store = I.Store()
I.ingest(sorted(d.glob("*.txt")), store, echo=False)
(d / "desk-lamp-dl1.txt").rename(d / "lamp-renamed.txt")
r = I.ingest(sorted(d.glob("*.txt")), store, echo=False)
assert r["new"] == 1 and len(store.chunks) == 12
assert I.duplicates(list(store.chunks.values())) == 0
print("test_ingest: OK")

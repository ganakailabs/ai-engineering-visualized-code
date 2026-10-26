"""The ingestion conveyor: stable ids, provenance and safe re-runs (Vol 3 Chapter 2).

load -> parse -> clean -> chunk -> embed -> index, with an id stamped on every chunk
from source + version + place, and a run manifest so a rerun after a crash skips what
finished, retries what failed, and leaves no duplicate or orphan chunk.
The manuals in vol3/knowledge/manuals/ are fictional fixtures, already extracted to text.
"""
import hashlib
import re
import uuid
from pathlib import Path

import _root  # noqa: F401

import events
from events import Trace
from store import TODAY
from stub_model import embed

MANUALS = Path(__file__).resolve().parent / "knowledge" / "manuals"
REQUIRED = ("id", "source", "version", "file", "page", "block", "sha256", "text")
events.KINDS.update({"load", "ingest", "rerun", "index"})   # Vol 3 (series contract section 4)


class Crash(Exception):
    """Scripted fault: the run dies partway through a file."""


class ProvenanceError(ValueError):
    """A chunk that cannot say where it came from never reaches the index."""


class _Clock:
    def now(self):
        return f"{TODAY.isoformat()}T09:00:00"


def chunk_id(source, version, page, block):
    return f"{source}@{version}:p{page}.b{block}"


def parse(path):
    """Header fields, then (page, block, raw text) for every blank-line block."""
    head, _, body = Path(path).read_text().partition("=== page ")
    meta = dict(re.findall(r"^(\w+): (.+)$", head, re.M))
    blocks = []
    for page in ("=== page " + body).split("=== page ")[1:]:
        num, _, text = page.partition("===")
        for b, raw in enumerate([x for x in text.split("\n\n") if x.strip()], 1):
            blocks.append((int(num), b, raw))
    return meta, blocks


def clean(raw):
    return re.sub(r"\s+", " ", raw).strip()


def check_provenance(chunk):
    missing = [f for f in REQUIRED if chunk.get(f) in (None, "")]
    if missing:
        raise ProvenanceError(f"{chunk.get('id', '?')}: missing {', '.join(missing)}")
    if chunk["id"] != chunk_id(chunk["source"], chunk["version"], chunk["page"], chunk["block"]):
        raise ProvenanceError(f"{chunk['id']}: id does not match its source and place")


def build(path):
    """Every stage except the commit: returns the file's chunks, all stamped."""
    data = Path(path).read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    meta, blocks = parse(path)
    chunks = []
    for page, block, raw in blocks:            # one block per chunk (Chapter 4 does sizes)
        text = clean(raw)
        c = {"id": chunk_id(meta["source"], meta["version"], page, block),
             "source": meta["source"], "version": meta["version"], "file": Path(path).name,
             "page": page, "block": block, "sha256": sha, "text": text, "vector": embed(text)}
        check_provenance(c)
        chunks.append(c)
    return meta, sha, chunks


class Store:
    """The index (chunks by id) and the run manifest, committed one file at a time."""

    def __init__(self):
        self.chunks = {}
        self.manifest = {"runs": [], "files": {}}


def ingest(files, store, crash_on=None, echo=True, run_id=None):
    run_id = run_id or f"run-{len(store.manifest['runs']) + 1}"
    t = Trace(_Clock(), "ingest", "-", run_id=run_id, echo=echo)
    t.emit("load", f"files={len(files)}")
    skipped = retried = new = changed = 0
    for i, f in enumerate(files, 1):
        f = Path(f)
        sha = hashlib.sha256(f.read_bytes()).hexdigest()
        rec = store.manifest["files"].get(f.name)
        if rec and rec["status"] == "ok" and rec["sha256"] == sha:
            skipped += 1
            continue
        retried += bool(rec and rec["status"] == "failed")
        new += rec is None
        changed += bool(rec and rec["status"] == "ok")
        meta, sha, chunks = build(f)
        if crash_on == i:
            store.manifest["files"][f.name] = dict(rec or {}, status="failed", sha256=sha)
            t.emit("ingest", f"file={i} crash (nothing committed)", file=f.name)
            raise Crash(f.name)
        old = set(rec["ids"]) if rec and "ids" in rec else set()
        for cid in old - {c["id"] for c in chunks}:    # an old version's chunks go too
            store.chunks.pop(cid, None)
        for c in chunks:                                # upsert by stable id
            store.chunks[c["id"]] = c
        store.manifest["files"][f.name] = {"status": "ok", "sha256": sha, "source": meta["source"],
                                           "version": meta["version"],
                                           "ids": [c["id"] for c in chunks]}
        t.emit("ingest", f"file={i} {meta['source']}@{meta['version']} chunks={len(chunks)}")
    if skipped or retried or changed:
        t.emit("rerun", f"skipped={skipped} retried={retried}"
                        + (f" changed={changed}" if changed else ""))
    t.emit("index", f"n={len(store.chunks)} duplicates={duplicates(list(store.chunks.values()))} "
                    f"orphans={len(orphans(store))}")
    store.manifest["runs"].append(run_id)
    return {"status": {Path(f).name: store.manifest["files"][Path(f).name]["status"] for f in files},
            "ids": list(store.chunks), "skipped": skipped, "retried": retried, "new": new, "changed": changed,
            "trace": t}


def duplicates(rows):
    """Rows whose content and place were already indexed under another id."""
    seen, dup = set(), 0
    for r in rows:
        key = (r["file"], r["page"], r["block"], r["text"])
        dup += key in seen
        seen.add(key)
    return dup


def orphans(store):
    """Indexed chunk ids that no finished file in the manifest claims."""
    live = {cid for rec in store.manifest["files"].values() if rec["status"] == "ok"
            for cid in rec.get("ids", [])}
    return sorted(set(store.chunks) - live)


# MM-070 Break: random ids, each chunk written the moment it is made, no manifest
class NaiveStore:
    def __init__(self):
        self.rows = []


def naive_ingest(files, store, crash_on=None):
    for i, f in enumerate(files, 1):
        meta, blocks = parse(f)
        for n, (page, block, raw) in enumerate(blocks):
            if crash_on == i and n == len(blocks) // 2:
                raise Crash(Path(f).name)
            store.rows.append({"id": str(uuid.uuid4()), "file": Path(f).name,
                               "page": page, "block": block, "text": clean(raw)})
    return store

"""The ingestion conveyor: stable ids, provenance and safe re-runs (Vol 3 Chapter 2).

load -> parse -> clean -> chunk -> embed -> index, with an id stamped on every chunk
from source + version + place, and a run manifest so a rerun after a crash skips what
finished, retries what failed, and leaves no duplicate or orphan chunk.
The manuals in vol3/knowledge/manuals/ are fictional fixtures, already extracted to text.

What this toy does and does not guarantee:
- Each file's changes are staged on copies of the index and manifest, then published
  as one immutable State(chunks, manifest) object: Store.publish() stores ONE reference,
  so a reader sees the whole old state or the whole new one. A crash before the publish
  leaves the published store as it was. That is the in-memory version of the idea; a durable atomic commit needs
  transactional or equivalent publication semantics in the real store (a database
  transaction, an alias swap, a write-then-rename on one filesystem).
- Store.save() writes a temporary file and renames it over the old one, so a restart
  reads either the old state or the new one, never half of each.
- A file is skipped only when its bytes (sha256) AND the pipeline fingerprint (parser,
  chunker and embedder settings in PIPELINE) both match the last good run. Change the
  chunker and every file is rebuilt.
- Each file's manifest record keeps the ACTIVE version (the last one committed: hash,
  fingerprint, source, version and chunk ids) apart from the LAST ATTEMPT (status, hash,
  error). A failed replacement records the failure in last_attempt and leaves active,
  and the published chunks, untouched: orphans() and the skip check read only active.
- The manifest is keyed by FILE NAME, not source identity. A renamed file is ingested
  again under its new name; stable ids keep that from duplicating chunks, but the old
  name's record stays until a lifecycle sync removes it (Chapter 14).
"""
import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import _root  # noqa: F401

import events
from events import Trace
from store import TODAY
from stub_model import embed

MANUALS = Path(__file__).resolve().parent / "knowledge" / "manuals"
REQUIRED = ("id", "source", "version", "file", "page", "block", "sha256", "text")
events.KINDS.update({"load", "ingest", "rerun", "index"})   # Vol 3 (series contract section 4)


# Everything that changes what a chunk or vector looks like. Part of the skip key.
PIPELINE = {"parser": "blank-line-blocks/1", "cleaner": "collapse-whitespace/1",
            "chunker": "one-block-per-chunk/1", "embedder": "stub_model.embed/1"}


def fingerprint(pipeline=None):
    blob = json.dumps(pipeline or PIPELINE, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


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


@dataclass(frozen=True)
class State:
    """One published state: the index (chunks by id) and the run manifest together.
    Frozen: nothing reassigns its fields; ingest() stages on copies and publishes a new
    State. (The inner dicts are not deep-frozen; by convention no one edits them after
    publication.)"""
    chunks: dict = field(default_factory=dict)
    manifest: dict = field(default_factory=lambda: {"runs": [], "files": {}})


class Store:
    """The published State, replaced one file at a time by a single reference store."""

    def __init__(self):
        self.state = State()

    @property
    def chunks(self):
        return self.state.chunks

    @property
    def manifest(self):
        return self.state.manifest

    def publish(self, state):
        """One reference store: readers see the old State or the new one, never a mix."""
        if not isinstance(state, State):
            raise TypeError("publish() takes one State(chunks, manifest)")
        self.state = state

    def save(self, path):
        """Write to a temporary file, then rename it over the old one (atomic on one
        filesystem), so a restart never loads a half-written store."""
        path = Path(path)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps({"chunks": self.chunks, "manifest": self.manifest}))
        os.replace(tmp, path)

    @classmethod
    def load(cls, path):
        s, data = cls(), json.loads(Path(path).read_text())
        s.publish(State(data["chunks"], data["manifest"]))
        return s


def status(store, name):
    """The last attempt's status for one file: "ok", "failed", or None if never tried."""
    rec = store.manifest["files"].get(name)
    return rec["last_attempt"]["status"] if rec else None


def ingest(files, store, crash_on=None, echo=True, run_id=None, crash_in_commit=None, pipeline=None):
    """crash_on=i dies after building file i; crash_in_commit=i dies halfway through
    staging file i's chunks. Either way nothing of file i is published."""
    fp = fingerprint(pipeline)
    run_id = run_id or f"run-{len(store.manifest['runs']) + 1}"
    t = Trace(_Clock(), "ingest", "-", run_id=run_id, echo=echo)
    t.emit("load", f"files={len(files)}")
    skipped = retried = new = changed = 0
    for i, f in enumerate(files, 1):
        f = Path(f)
        sha = hashlib.sha256(f.read_bytes()).hexdigest()
        rec = store.manifest["files"].get(f.name)
        active = rec["active"] if rec else None
        failed_before = bool(rec and rec["last_attempt"]["status"] == "failed")
        if active and active["sha256"] == sha and active.get("fingerprint") == fp:
            if failed_before:            # the bytes went back to the active version
                _record(store, f.name, active, dict(status="ok", sha256=sha, error=None))
            skipped += 1
            continue
        retried += failed_before
        new += rec is None
        changed += bool(active) and not failed_before
        meta, sha, chunks = build(f)
        if crash_on == i:
            _mark_failed(store, f.name, active, sha, "crash after build")
            t.emit("ingest", f"file={i} crash (nothing committed)", file=f.name)
            raise Crash(f.name)
        staged = dict(store.chunks)                      # stage on copies ...
        old = set(active["ids"]) if active else set()
        for cid in old - {c["id"] for c in chunks}:    # an old version's chunks go too
            staged.pop(cid, None)
        for n, c in enumerate(chunks):                  # upsert by stable id
            if crash_in_commit == i and n == len(chunks) // 2:
                _mark_failed(store, f.name, active, sha, "crash mid-commit")
                t.emit("ingest", f"file={i} crash mid-commit (nothing published)", file=f.name)
                raise Crash(f.name)
            staged[c["id"]] = c
        new_active = {"sha256": sha, "fingerprint": fp, "source": meta["source"],
                      "version": meta["version"], "ids": [c["id"] for c in chunks]}
        files_rec = dict(store.manifest["files"],
                         **{f.name: {"active": new_active,
                                     "last_attempt": dict(status="ok", sha256=sha, error=None)}})
        store.publish(State(staged, dict(store.manifest, files=files_rec)))   # ... then one store
        t.emit("ingest", f"file={i} {meta['source']}@{meta['version']} chunks={len(chunks)}")
    if skipped or retried or changed:
        t.emit("rerun", f"skipped={skipped} retried={retried}"
                        + (f" changed={changed}" if changed else ""))
    t.emit("index", f"n={len(store.chunks)} duplicates={duplicates(list(store.chunks.values()))} "
                    f"orphans={len(orphans(store))}")
    store.publish(State(store.chunks, dict(store.manifest, runs=store.manifest["runs"] + [run_id])))
    return {"status": {Path(f).name: status(store, Path(f).name) for f in files},
            "ids": list(store.chunks), "skipped": skipped, "retried": retried, "new": new, "changed": changed,
            "trace": t}


def _record(store, name, active, attempt):
    files = dict(store.manifest["files"], **{name: {"active": active, "last_attempt": attempt}})
    store.publish(State(store.chunks, dict(store.manifest, files=files)))


def _mark_failed(store, name, active, sha, error):
    """Record the failed attempt; the active version and the published chunks stay."""
    _record(store, name, active, dict(status="failed", sha256=sha, error=error))


def duplicates(rows):
    """Rows whose content and place were already indexed under another id."""
    seen, dup = set(), 0
    for r in rows:
        key = (r["file"], r["page"], r["block"], r["text"])
        dup += key in seen
        seen.add(key)
    return dup


def orphans(store):
    """Indexed chunk ids that no file's ACTIVE (last committed) version claims. A failed
    later attempt does not orphan the chunks of the version still being served."""
    live = {cid for rec in store.manifest["files"].values() if rec["active"]
            for cid in rec["active"]["ids"]}
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

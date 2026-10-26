"""Chapter 2: Ingestion Pipelines: Stable IDs, Provenance and Re-Runs.

Run from the repo root:  python3 vol3/ch02.py
Real model (optional, Part 4 only):  AIEV_MODEL=ollama:llama3.2 python3 vol3/ch02.py
Ingests the three fixture manuals in vol3/knowledge/manuals/ (fictional, pre-extracted
text). Parts 1-3 use no model at all. Part 4 shows what duplicates do to the top 3
passages a model would be given (Vol 1 keyword search).
"""
import textwrap
import shutil
import tempfile
from pathlib import Path

import _root  # noqa: F401

import ingest as I
import llm
from ch13 import keyword_score

FILES = sorted(I.MANUALS.glob("*.txt"))
CHARGE = "How do I charge the NW-500 headphones?"


def top3(question, rows):
    ranked = sorted(rows, key=lambda r: -keyword_score(question, r["text"]))
    return [f"{r['file'].split('.')[0]}:p{r['page']}.b{r['block']}" for r in ranked[:3]]


if __name__ == "__main__":
    print("Part 1 (MM-148): every chunk knows its source")
    store = I.Store()
    I.ingest(FILES, store)
    c = store.chunks["man-nw500@2026-07-01:p2.b2"]
    print(f"  {c['id']}  file={c['file']} page={c['page']} block={c['block']}\n"
          f"    sha256={c['sha256'][:12]}...")
    print("  text: " + textwrap.fill(c["text"], 66, subsequent_indent="    ")[0:])

    print("\nPart 2 (MM-070 Break): random ids, crash on file 2, full rerun")
    naive = I.NaiveStore()
    try:
        I.naive_ingest(FILES, naive, crash_on=2)
    except I.Crash as e:
        print(f"  crash  file=2 ({e}) after {len(naive.rows)} rows written")
    I.naive_ingest(FILES, naive)
    print(f"  rerun  rows={len(naive.rows)} duplicates={I.duplicates(naive.rows)} "
          f"(a clean run has {len(store.chunks)})")

    print("\nPart 3 (MM-070 Fix): stable ids, commit per file, manifest")
    work = Path(tempfile.mkdtemp())
    files = [Path(shutil.copy(f, work / f.name)) for f in FILES]
    fixed = I.Store()
    try:
        I.ingest(files, fixed, crash_on=2)
    except I.Crash:
        pass
    I.ingest(files, fixed)
    print(f"  same ids as the clean run: {sorted(fixed.chunks) == sorted(store.chunks)}")
    lamp = work / "desk-lamp-dl1.txt"
    lamp.write_text(lamp.read_text().replace("version: 2026-05-10", "version: 2026-10-01"))
    print("  the desk lamp manual gets a new version:")
    I.ingest(files, fixed)

    print(f"\nPart 4: top 3 passages for {CHARGE!r}")
    print(f"  naive index: {top3(CHARGE, naive.rows)}")
    print(f"  fixed index: {top3(CHARGE, list(store.chunks.values()))}")
    if llm.name() != "stub":                     # Model experiment (see vol3/runs/README.md)
        from ch15 import augment, generate
        for label, rows in (("naive", naive.rows), ("fixed", list(store.chunks.values()))):
            ranked = sorted(rows, key=lambda r: -keyword_score(CHARGE, r["text"]))[:3]
            passages = {f"{r['file'].split('.')[0]}:p{r['page']}.b{r['block']}#{n}": r["text"]
                        for n, r in enumerate(ranked)}
            print(f"  {llm.name()} ({label}): {generate(augment(passages), CHARGE)}")

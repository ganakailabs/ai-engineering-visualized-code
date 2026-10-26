# AI Engineering Visualized, Vol 3: companion code (`vol3/`)

`vol3/` is the companion code for **AI Engineering Visualized, Volume 3: RAG & Knowledge
Systems**. It keeps building the same Northwind Goods support assistant and gives it real
knowledge: source contracts, an ingestion pipeline, and (in later chapters) parsing,
chunking, indexes and retrieval metrics. It reuses Vol 2 (`../vol2/`) and Vol 1 (`../vol1/`)
unchanged; `_root.py` puts both on the import path, so keep the three folders together.
Python 3.10+, standard library only for Chapters 1-2; the stub is the default.

**Status:** work in progress. Chapters 1-2 are drafted; the rest of the volume is not written yet.

## Start here

From the repo root:

    python3 vol3/start.py              # the assistant Vol 2 finished, run from vol3/
    python3 vol3/ch01.py               # one chapter
    python3 vol3/run_solutions.py      # every Vol 3 solution and test; ends with "all passed"

With a real local model (after `ollama pull llama3.2` and `ollama serve`, see `../vol1/README.md`):

    AIEV_MODEL=ollama:llama3.2 python3 vol3/ch01.py

A 3B model will often differ from the book's printed output; code validates every reply
and turns a bad one into an escalation. `vol3/run_solutions.py` always checks the stub.
The exact commands for the real-model runs are in [`runs/README.md`](runs/README.md).

## vol3-start

`vol3-start` is Vol 2's final code: commit `fa57112` of this repo (`vol1/` + `vol2/`),
whose `vol2/run_solutions.py` passes on the stub. `vol3/` adds files only; it changes
nothing in `vol1/` or `vol2/`. `tests/test_start.py` checks that Vol 2's agentic
retrieval still answers the mug ticket from `vol3/`.

| File | Chapter |
|---|---|
| `start.py` | Before You Start: the assistant so far |
| `knowledge/` | fixture sources (fictional): `sources.json` contracts, three product manuals as pre-extracted text, six past tickets |
| `sources.py`, `ch01.py` | Ch 1: source contracts, `route()`, `fetch()`, `check_decision()` |
| `ingest.py`, `ch02.py` | Ch 2: stable chunk ids, provenance, run manifest, safe re-runs |
| `solutions/` | exercise solutions (`ch01_solution.py`, `ch02_solution.py`) |
| `tests/` | implementation tests (stub only) |
| `runs/` | real-model run logs (none yet) |

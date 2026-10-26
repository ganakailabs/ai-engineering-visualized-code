# AI Engineering Visualized: companion code

Companion code for the **AI Engineering Visualized** series by Prateek Singh / Ganak AI Labs.
Every volume builds the same Northwind Goods support assistant, one folder per volume.
Python 3.10+. Vol 1 uses the standard library only; Vol 2 Chapters 12-13 (and the Vol 2 suite)
also need the official MCP Python SDK, pinned in `requirements.txt` (`mcp==2.3.0`). A scripted
stub model is the default, so no API key, network or cost is needed. Run every command from the repo root (this folder).

| Folder | Book | Run |
|---|---|---|
| [`vol1/`](vol1/) | Vol 1: A Visual Guide to Building LLM Apps, RAG and Agents (Ch 1-24) | `python3 vol1/run_all.py` |
| [`vol2/`](vol2/) | Vol 2: Agents in production (Ch 1-17) | `pip install -r requirements.txt`, then `python3 vol2/run_solutions.py` |
| [`vol3/`](vol3/) | Vol 3: RAG & Knowledge Systems (in progress: Ch 1-2) | `python3 vol3/run_solutions.py` |

Get the book: https://leanpub.com/ai-engineering-visualized

## vol1/

Chapters `vol1/ch01.py` ... `vol1/ch24.py`, exercise solutions in `vol1/solutions/`, tests in
`vol1/tests/`. See [`vol1/README.md`](vol1/README.md) for the stub model and the optional
Ollama setup (`AIEV_MODEL=ollama:llama3.2`).

    python3 vol1/run_all.py         # every chapter, then every exercise solution
    python3 vol1/ch05.py            # one chapter

## vol2/

Chapters `vol2/ch01.py` ... `vol2/ch17.py`, solutions in `vol2/solutions/`, tests in
`vol2/tests/`, real-model run logs in `vol2/runs/`. Vol 2 reuses the Vol 1 modules from
`vol1/` (via `vol2/_root.py`), so keep both folders together. See
[`vol2/README.md`](vol2/README.md).

    python3 vol2/run_solutions.py   # every Vol 2 exercise solution and test
    python3 vol2/ch01.py            # one chapter

## vol3/ (in progress)

Chapters `vol3/ch01.py` and `vol3/ch02.py`, fixture sources in `vol3/knowledge/`, solutions in
`vol3/solutions/`, tests in `vol3/tests/`. Vol 3 reuses `vol2/` and `vol1/` (via `vol3/_root.py`).
See [`vol3/README.md`](vol3/README.md).

    python3 vol3/run_solutions.py   # every Vol 3 exercise solution and test

## License

Code: MIT (see LICENSE). The book text and illustrations are not covered by this license.

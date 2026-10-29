# AI Engineering Visualized, Vol 3: companion code (`vol3/`)

`vol3/` is the companion code for **AI Engineering Visualized, Volume 3: RAG & Knowledge
Systems**. It keeps building the same Northwind Goods support assistant and gives it real
knowledge: source contracts, ingestion, layout parsing, chunking, access control,
vector and hybrid search, reranking, query understanding, precedence, context
assembly, structured queries, graphs, index lifecycle, metrics and regression gates. It reuses Vol 2 (`../vol2/`) and Vol 1 (`../vol1/`)
unchanged; `_root.py` puts both on the import path, so keep the three folders together.
Python 3.10+, standard library only; the stub is the default. Optional real-model,
parser, vision and reranker runs need extra installs (see [`runs/README.md`](runs/README.md)).

**Status:** all 16 chapters and the capstone have code, exercise solutions and stub tests;
`run_solutions.py` ends with "all passed". Each chapter's code is a teaching fixture: it
demonstrates one mechanism on a small fictional dataset and is not a production component.
Real-model results logged so far are in `runs/`; experiments that need hand grading are
marked `[TO MEASURE]` in the book until graded.

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
| `knowledge/` | fixture sources (fictional): `sources.json` contracts, product manuals as pre-extracted text, past tickets, the returns handbook, layout pages |
| `sources.py`, `ch01.py` | Ch 1: source contracts, `route()`, `fetch()`, `check_decision()` |
| `ingest.py`, `ch02.py` | Ch 2: stable chunk ids, provenance, run manifest, staged commit, pipeline fingerprint, safe re-runs |
| `layout.py`, `ch03.py` | Ch 3: layout-aware parsing, table rows, OCR confidence (optional pdfplumber and vision paths) |
| `chunking.py`, `ch04.py` | Ch 4: heading chunks, small-to-big, applicability tags and dates |
| `access.py`, `ch05.py` | Ch 5: tenant and audience filter at search, expand, rerank, cache and cite |
| `vectors.py`, `ch06.py` | Ch 6: embedder contracts, recall on a golden set, a clustered (IVF-style) index |
| `hybrid.py`, `ch07.py` | Ch 7: BM25 plus meaning scores, score fusion and RRF, an exact-id priority lane |
| `rerank.py`, `ch08.py` | Ch 8: first stage plus reranker over 40 chunks (optional cross-encoder) |
| `query.py`, `ch09.py` | Ch 9: rewrite, surface-fact retention check, route or clarify |
| `precedence.py`, `ch10.py` | Ch 10: source authority, conflicts, abstain floors |
| `assemble.py`, `ch11.py` | Ch 11: dedupe, ordering, token budget, citation check, coverage per k |
| `structured.py`, `ch12.py` | Ch 12: QuerySpecs, session-bound scope, parameterized SQL |
| `graph.py`, `ch13.py` | Ch 13: entity resolution, edge provenance, covered / excluded / unknown |
| `lifecycle.py`, `ch14.py` | Ch 14: content, access, version and delete sync; build, check, switch |
| `metrics.py`, `ch15.py` | Ch 15: retrieval and answer metrics, a pairwise judge check |
| `gate.py`, `ch16.py` | Ch 16: synthetic test sets, held-out split, regression gate |
| `capstone.py` | Capstone: a tour of the implemented stages (each on its own fixture) |
| `pipeline.py` | Connected capstone: one request path through Ch 1–16 over one corpus, with a work-count budget and a gate over its own output |
| `solutions/` | exercise solutions, `ch01_solution.py` ... `ch16_solution.py` |
| `tests/` | implementation tests (stub only), including the edge cases from the external review |
| `runs/` | real-model run logs and how to reproduce them; see [`runs/README.md`](runs/README.md) |

## Reporting a problem

Open an issue at https://github.com/ganakailabs/ai-engineering-visualized-code/issues with:
the book volume and chapter, the command you ran, your Python version and OS, whether
`AIEV_MODEL` (or another `AIEV_*` variable) was set, what you expected, and what you got
(paste the output).

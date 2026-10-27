# Real-model runs (Vol 3)

Every model output in the Vol 3 manuscript that would come from a real model is marked
`[TO MEASURE]` until a run is logged here. Recorded so far (Oct 27, 2026): Ch 1, 2, 3, 6,
9, 11 (citations), 12. Ollama ids are in `2026-10-27-models.txt`.

Runs are made on a Mac with Ollama and `llama3.2` (3B), from the repo root, with the
same pinned settings as Vol 2 (`SEED 7`, `TEMPERATURE 0.0` in `vol2/llm.py`). Save each
log as `YYYY-MM-DD-llama3.2-<what>.txt` in this folder.

## Setup (once)

    ollama pull llama3.2
    ollama serve                       # in another terminal
    ollama list                        # note the llama3.2 digest in the log header

## Chapter 1: classify and route

    AIEV_MODEL=ollama:llama3.2 python3 vol3/ch01.py 2>&1 | tee vol3/runs/$(date +%F)-llama3.2-ch01.txt

What to record (fills the `[TO MEASURE]` marks in Ch 1): for each of the six questions
in Part 2, the needs llama3.2 named and whether `validate_needs` accepted them; whether
Part 3's routed answer still decides `refund or replace (R2)`.

## Chapter 2: duplicates in the model's context

    AIEV_MODEL=ollama:llama3.2 python3 vol3/ch02.py 2>&1 | tee vol3/runs/$(date +%F)-llama3.2-ch02.txt

Parts 1-3 do not call a model. Part 4 sends the top 3 passages from the naive and the
fixed index to llama3.2. Note: with `AIEV_MODEL` set, Vol 1's `embed()` also asks Ollama
for embeddings, so Ollama must be running for the whole script.

## Exercise solutions on the real model

    AIEV_MODEL=ollama:llama3.2 python3 vol3/run_solutions.py --real 2>&1 | tee vol3/runs/$(date +%F)-llama3.2-solutions.txt

Tests always run on the stub; `--real` sends only the solutions to the model.

## Chapter 3: documents with layout
Confirmed choices (decision D3-11, confirmed by the owner Oct 27, 2026): pdfplumber
0.11.10 for the parser and `qwen2.5vl:3b` for the vision path. Venvs use uv with Python
3.12 (Homebrew's Python 3.14 venv failed at ensurepip).
- Parser: `uv venv --python 3.12 .venv-parse && uv pip install --python .venv-parse pdfplumber==0.11.10`, then `AIEV_PARSER=pdfplumber .venv-parse/bin/python vol3/ch03.py 2>&1 | tee vol3/runs/$(date +%F)-ch03-pdfplumber.txt`.
- Vision: `ollama pull qwen2.5vl:3b`, then `AIEV_VISION=qwen2.5vl:3b .venv-parse/bin/python vol3/ch03.py 2>&1 | tee vol3/runs/$(date +%F)-ch03-qwen2.5vl.txt`.

## Chapters 4 and 5
No model needed; the stub output in the chapter is the real output.

## Chapter 6: embedding models
`ollama pull nomic-embed-text && ollama pull mxbai-embed-large`, then
`AIEV_EMBED=nomic-embed-text,mxbai-embed-large python3 vol3/ch06.py 2>&1 | tee vol3/runs/$(date +%F)-ch06-embed.txt`. Record recall@1 per model in place of [TO MEASURE] in Ch 6.

## Chapter 8: a real reranker
`uv venv --python 3.12 .venv-rerank && uv pip install --python .venv-rerank sentence-transformers`, then
`AIEV_RERANKER=cross-encoder/ms-marco-MiniLM-L6-v2 .venv-rerank/bin/python vol3/ch08.py`.
Record reranked recall@5 per net size in place of [TO MEASURE] in Ch 8.

## Chapter 9: a real rewriter
`AIEV_MODEL=ollama:llama3.2 python3 vol3/ch09.py 2>&1 | tee vol3/runs/$(date +%F)-llama3.2-ch09.txt`.
Record the rewritten parts and the check line for the two-part ticket in place of
[TO MEASURE] in Ch 9. If the check fails, the script asks the customer instead of searching; record that too.

## Chapter 10
No model needed for precedence; the stub output is the real output. Abstain floors on a
real model and scorer must be recalibrated: score your own dev cases per source, then run
`calibrate()` on them. Record the floors in place of [TO MEASURE] in Ch 10.

## Chapter 11: a real model on the evidence pack
`AIEV_MODEL=ollama:llama3.2 python3 vol3/ch11.py 2>&1 | tee vol3/runs/$(date +%F)-llama3.2-ch11.txt`.
Record which labels the reply cites and whether `validate_citations()` passes, in place of
the first [TO MEASURE] in Ch 11. For accuracy per k, answer the six held-out questions with
`pack_for(question, k)` at k = 2, 3, 5, 10, grade each reply by hand against the needed
passages, and record correct/6 per k. The distraction experiment is the same run with one
unrelated passage added to each pack.

## Chapter 12: a real model filling QuerySpecs
`AIEV_MODEL=ollama:llama3.2 python3 vol3/ch12.py 2>&1 | tee vol3/runs/$(date +%F)-llama3.2-ch12.txt`.
Record, per question, whether the spec validated, and the rows returned. Specs that fail
validation are refused, never repaired; count them.

## Chapter 13: graph hops vs plain RAG
For each part asked about in `vol3/ch13.py` ("NW charger", "NW-500 ear tips", "NW-500 cable"),
record the verdict and path from `graph.coverage(part)`, then answer the same question with plain retrieval (Ch 6 index, k=5) on
`AIEV_MODEL=ollama:llama3.2`. Record, per method, correct/total, model calls and tokens
in place of [TO MEASURE] in Ch 13.

## Chapter 14: a real embedder migration
Build `INDEX v1` and `INDEX v2` with two real embedders (for example `nomic-embed-text`
and `mxbai-embed-large` from Ch 6) by passing `model="ollama:nomic-embed-text"` and `model="ollama:mxbai-embed-large"` to
`build(src, name, model)`, then run
`check()` and `switch()`. Record held-out recall for each and whether the switch happened,
in place of [TO MEASURE] in Ch 14.

## Chapter 15: a real judge
Write a judge function `judge(question, first, second)` that asks
`ollama:llama3.2` (via `llm.ask_json`) which reply is better supported and returns
`"first"` or `"second"`. Then run `metrics.agreement(judge)`, `metrics.flips(judge)` and
`metrics.trusted(judge)` on the ten `metrics.PAIRS`. Record agreement, flips and the
labelled-set size (10) in place of [TO MEASURE] in Ch 15.

## Chapter 16: the held-out suite on a real model
Answer each `gate.BENCH` case with the full pipeline on `AIEV_MODEL=ollama:llama3.2`,
grade it by hand as correct, wrong or abstained, and replace the scripted results with
yours. Record model, settings, the per-case sheet and the `gate()` verdict in place of
[TO MEASURE] in Ch 16.

# Real-model runs (Vol 3)

No real-model runs have been recorded yet. Every model output in the Vol 3 manuscript
that would come from a real model is marked `[TO MEASURE]` until a run is logged here.

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

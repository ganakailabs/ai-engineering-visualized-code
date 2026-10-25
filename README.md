# AI Engineering Visualized, Vol 1: companion code

Companion code for **AI Engineering Visualized: A Visual Guide to Building LLM Apps, RAG and
Agents, Volume 1** by Prateek Singh / Ganak AI Labs.
Get the book (early access): https://leanpub.com/ai-engineering-visualized

The code builds one support assistant for Northwind Goods, a fictional online store,
chapter by chapter.

## Run it

Python 3.10+ and the standard library only. No API key, no network, no cost.

    python3 run_all.py          # every chapter, then every exercise solution
    python3 run_solutions.py    # exercise solutions only (each checks its own result)
    python3 ch01.py             # one chapter
    python3 ch24.py             # watch the whole agent work, step by step

## The stub model

`stub_model.py` replaces the real model call with a local, **scripted** stand-in that has
the same reply shape as a chat API (`{"text", "usage", "finish_reason"}`, plus
`"tool_calls"` in Chapter 11). It reproduces the
failure each chapter teaches so you can watch the mechanics. A real model may fail the same
way, differently, or not at all on your tickets; that is why the book teaches you to measure.
To use a real provider, replace the body of `call_model()` with your SDK call and keep the
return shape. Chapter 9's three models, their prices and speeds, and Chapter 12's
`embed()` are toys made up for the demos, not measurements of any real model.
`store.py` holds the fictional store data: policy clauses and orders.

## Run with a real local model (optional): Ollama

Ollama runs open models on your own computer, with no key and no bill. `ollama_model.py`
is an adapter behind the same `call_model()` (standard library only, one POST to
`http://localhost:11434/api/chat`); the stub stays the default.

Install from https://ollama.com/download, or `brew install ollama` on a Mac, or on Linux:

    curl -fsSL https://ollama.com/install.sh | sh

Pull a small model and start the server (the desktop app starts it for you; skip
`ollama serve` if it is already running):

    ollama pull llama3.2
    ollama serve

`llama3.2` is about 2 GB and supports tool calling. With 16 GB of memory or more you can
try a larger one, such as `gpt-oss:20b` (about 14 GB). The library changes, so check
https://ollama.com/library for current names and sizes.

Then point the code at it with one environment variable, in a second terminal:

    export AIEV_MODEL=ollama:llama3.2    # PowerShell: $env:AIEV_MODEL="ollama:llama3.2"
    python3 ch06.py                      # the Chapter 6 position eval
    python3 ch08.py                      # the Chapter 8 evals
    python3 ch24.py                      # the Chapter 24 agent run
    unset AIEV_MODEL                     # back to the stub

If Ollama is not running, the code stops with a message that says so. A real model
follows only the format it is shown, so on this path the adapter adds the exact output
format to each prompt, with a tiny example (`formats.py`), and asks for JSON mode where
JSON is expected. Replies are then read tolerantly (`parse.py`): a reply that still
cannot be parsed becomes a safe `escalate`, with the reason printed, never a crash.
Real-model output will differ from the expected outputs printed in the book, and that
is the point: compare them, and let the evals tell you what changed. Tool calling needs a model that supports
it; if yours does not, the adapter asks again without tools and says why.
`run_solutions.py` always checks the stub, because its checks match the stub's scripted
answers (`tests/test_ollama_adapter.py` checks the adapter's request with no network).

## Chapters

| File | Chapter |
|---|---|
| `ch01.py` | 1. AI Engineering Is a System |
| `ch02.py` | 2. What an LLM Is: From Text Predictor to Assistant |
| `ch03.py` | 3. Talking to a Model: The Chat API |
| `ch04.py` | 4. Tokens: What the Model Reads and What You Pay |
| `ch05.py` | 5. One Token at a Time: Why Answers Vary |
| `ch06.py` | 6. Inside the Context Window: What the Model Pays Attention To |
| `ch07.py` | 7. Fluent Is Not True: Hallucination |
| `ch08.py` | 8. Evals: Measuring a Probabilistic System |
| `ch09.py` | 9. Choosing a Model |
| `ch10.py` | 10. Anatomy of a Prompt |
| `ch11.py` | 11. Structured Output and Tool Calling |
| `ch12.py` | 12. Embeddings: Meaning as Coordinates |
| `ch13.py` | 13. Search and Retrieval: Finding the Right Passage |
| `ch14.py` | 14. Chunking: Cutting Documents So the Right Piece Is Found |
| `ch15.py` | 15. The RAG Pipeline: Retrieve, Then Answer |
| `ch16.py` | 16. Grounded Answers: Citations and "I Don't Know" |
| `ch17.py` | 17. Is the RAG Working? Evaluating Retrieval and Answers |
| `ch18.py` | 18. Workflows vs Agents: Rails or Steering Wheel |
| `ch19.py` | 19. The Agent Loop: Think, Act, Observe |
| `ch20.py` | 20. Planning and Multi-Step Tasks |
| `ch21.py` | 21. Memory: What the Agent Remembers |
| `ch22.py` | 22. Agent Safety: Permissions, Approvals and the Trojan Ticket |
| `ch23.py` | 23. Guardrails and Privacy: Checks In, Checks Out |
| `ch24.py` | 24. Ship It: Errors, Tracing, Latency and the Complete System |

Chapters 7-24 are in first draft and not yet in the published early-access edition.

## Exercise solutions

`solutions/chNN_solution.py` solves the Exercise at the end of chapter NN. Each runs on its
own (`python3 solutions/ch01_solution.py`) and exits non-zero if its check fails.

## Vol 2: agents in production (`v2/`)

`v2/` is the companion code for **AI Engineering Visualized, Volume 2**. It keeps building
the same Northwind Goods support assistant, now as an agent with a harness, tools, plans,
checkpoints, approvals, memory, MCP servers and evals. It reuses the Vol 1 modules in this
folder (`store.py`, `parse.py`, `stub_model.py`, `ollama_model.py`, ...), so keep `v2/`
inside this repo. Python 3.10+ and the standard library only; the stub is the default.

Run from the repo root:

    python3 v2/ch01.py               # one chapter
    python3 v2/run_solutions.py      # every Vol 2 exercise solution and test

With a real local model, after `ollama pull llama3.2` and `ollama serve` (see above):

    AIEV_MODEL=ollama:llama3.2 python3 v2/ch01.py
    # PowerShell: $env:AIEV_MODEL="ollama:llama3.2"; python3 v2/ch01.py

A 3B model like `llama3.2` will often differ from the book's printed output, and
sometimes fail a step; the harness turns a bad reply into a stop or an escalation, never a
crash. `v2/runs/` holds logs of real `llama3.2` runs, so you can compare yours.
`v2/run_solutions.py` always checks the stub.

Chapter 12's interop step has the official MCP TypeScript client call our server. It is
optional and needs Node.js: run `npm ci` in `v2/interop` once; without it the step prints
`skipped`.

| File | Chapter |
|---|---|
| `v2/ch01.py` | 1. The Agent Harness: Everything Around the Model |
| `v2/ch02.py` | 2. Tool Engineering: Schemas, Validation and Safe Actions |
| `v2/ch03.py` | 3. Planning: Dependencies, Validation and Replanning |
| `v2/ch04.py` | 4. Verification Before Commit: Checks, Bounded Revision and Postconditions |
| `v2/ch05.py` | 5. State Machines, Checkpoints and Stop Reasons |
| `v2/ch06.py` | 6. Side Effects: Idempotency, Transactions and Compensation |
| `v2/ch07.py` | 7. Long-Running Tickets: Waits, Progress and Cancellation |
| `v2/ch08.py` | 8. Human Oversight: Approvals, Interrupts and Escalations |
| `v2/ch09.py` | 9. Agent Memory: Lifetime, Scope and Correction |
| `v2/ch10.py` | 10. Context Engineering for Long-Running Agents |
| `v2/ch11.py` | 11. Agentic RAG: Retrieval the Agent Chooses |
| `v2/ch12.py` | 12. MCP: Hosts, Clients, Servers and Discovery |
| `v2/ch13.py` | 13. Tool Trust: Credentials, Allow-Lists and Untrusted Output |
| `v2/ch14.py` | 14. Multi-Agent Systems: Handoffs, Coordination and Trade-offs |
| `v2/ch15.py` | 15. Agent Failure Engineering: Loops, Cascades and Side Effects |
| `v2/ch16.py` | 16. Agent Evaluation: Outcomes and Trajectories |
| `v2/ch17.py` | 17. Agent Reliability: Repeat Runs, Scorecards and Gates |

Exercise solutions are in `v2/solutions/chNN_solution.py`; tests in `v2/tests/`.

## License

Code: MIT (see LICENSE). The book text and illustrations are not covered by this license.

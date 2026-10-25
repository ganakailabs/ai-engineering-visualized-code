# AI Engineering Visualized, Vol 2: companion code (`vol2/`)

`vol2/` is the companion code for **AI Engineering Visualized, Volume 2**. It keeps building
the same Northwind Goods support assistant, now as an agent with a harness, tools, plans,
checkpoints, approvals, memory, MCP servers and evals. It reuses the Vol 1 modules in `../vol1/`
(`store.py`, `parse.py`, `stub_model.py`, `ollama_model.py`, ...; `_root.py` puts that folder on
the import path), so keep `vol2/` next to `vol1/` in this repo. Python 3.10+; the stub is the default.
Chapters 12-13 (MCP servers, host and trust) and `run_solutions.py` need `mcp==2.3.0`;
every other chapter is standard library only.

## Start here

From the repo root:

    python3 -m venv .venv
    source .venv/bin/activate            # Windows: .venv\Scripts\activate
    python -m pip install -r requirements.txt
    python vol2/run_solutions.py         # ends with "all passed"

## Troubleshooting

- `ModuleNotFoundError: No module named 'mcp'`: the venv is not active, or `pip install -r
  requirements.txt` was not run in it.
- `ModuleNotFoundError` for `store`, `parse` or `stub_model`: `vol2/` was copied without
  `vol1/`; keep both folders from this repo together.
- Python older than 3.10: the code uses 3.10 syntax; check `python --version`.
- Chapter 12 prints `skipped` for interop: expected without Node.js (see below).
- With `AIEV_MODEL=ollama:llama3.2`, connection refused: start `ollama serve`; output that
  differs from the book is expected for a 3B model.

Run from the repo root:

    python3 vol2/ch01.py               # one chapter
    python3 vol2/run_solutions.py      # every Vol 2 exercise solution and test

With a real local model, after `ollama pull llama3.2` and `ollama serve` (see `../vol1/README.md`):

    AIEV_MODEL=ollama:llama3.2 python3 vol2/ch01.py
    # PowerShell: $env:AIEV_MODEL="ollama:llama3.2"; python3 vol2/ch01.py

A 3B model like `llama3.2` will often differ from the book's printed output, and
sometimes fail a step; the harness turns a bad reply into a stop or an escalation, never a
crash. `vol2/runs/` holds logs of real `llama3.2` runs, so you can compare yours.
`vol2/run_solutions.py` always checks the stub.

Chapter 12's interop step has the official MCP TypeScript client call our server. It is
optional and needs Node.js: run `npm ci` in `vol2/interop` once; without it the step prints
`skipped`.

| File | Chapter |
|---|---|
| `vol2/ch01.py` | 1. The Agent Harness: Everything Around the Model |
| `vol2/ch02.py` | 2. Tool Engineering: Schemas, Validation and Safe Actions |
| `vol2/ch03.py` | 3. Planning: Dependencies, Validation and Replanning |
| `vol2/ch04.py` | 4. Verification Before Commit: Checks, Bounded Revision and Postconditions |
| `vol2/ch05.py` | 5. State Machines, Checkpoints and Stop Reasons |
| `vol2/ch06.py` | 6. Side Effects: Idempotency, Transactions and Compensation |
| `vol2/ch07.py` | 7. Long-Running Tickets: Waits, Progress and Cancellation |
| `vol2/ch08.py` | 8. Human Oversight: Approvals, Interrupts and Escalations |
| `vol2/ch09.py` | 9. Agent Memory: Lifetime, Scope and Correction |
| `vol2/ch10.py` | 10. Context Engineering for Long-Running Agents |
| `vol2/ch11.py` | 11. Agentic RAG: Retrieval the Agent Chooses |
| `vol2/ch12.py` | 12. MCP: Hosts, Clients, Servers and Discovery |
| `vol2/ch13.py` | 13. Tool Trust: Credentials, Allow-Lists and Untrusted Output |
| `vol2/ch14.py` | 14. Multi-Agent Systems: Handoffs, Coordination and Trade-offs |
| `vol2/ch15.py` | 15. Agent Failure Engineering: Loops, Cascades and Side Effects |
| `vol2/ch16.py` | 16. Agent Evaluation: Outcomes and Trajectories |
| `vol2/ch17.py` | 17. Agent Reliability: Repeat Runs, Scorecards and Gates |
| `vol2/capstone.py` | Capstone: one ticket through policy, approval, ledger, handoff and the gate |

Exercise solutions are in `vol2/solutions/chNN_solution.py`; tests in `vol2/tests/`.

## License

Code: MIT (see ../LICENSE). The book text and illustrations are not covered by this license.

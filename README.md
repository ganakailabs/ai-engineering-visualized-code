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

## License

Code: MIT (see LICENSE). The book text and illustrations are not covered by this license.

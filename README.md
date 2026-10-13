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
the same reply shape as a chat API (`{"text", "usage", "finish_reason"}`). It reproduces the
failure each chapter teaches so you can watch the mechanics. A real model may fail the same
way, differently, or not at all on your tickets; that is why the book teaches you to measure.
To use a real provider, replace the body of `call_model()` with your SDK call and keep the
return shape. `store.py` holds the fictional store data: policy clauses and orders.

## Chapters

| File | Chapter |
|---|---|
| `ch01.py` | 1. AI Engineering Is a System |
| `ch02.py` | 2. What an LLM Is: From Text Predictor to Assistant |
| `ch03.py` | 3. Talking to a Model: The Chat API |
| `ch04.py` | 4. Tokens: What the Model Reads and What You Pay |
| `ch05.py` | 5. One Token at a Time: Why Answers Vary |
| `ch06.py` | 6. Inside the Context Window: What the Model Pays Attention To |
| `ch07.py` | 7. Fluent Is Not True (chapter not yet published) |

## Exercise solutions

`solutions/chNN_solution.py` solves the Exercise at the end of chapter NN. Each runs on its
own (`python3 solutions/ch01_solution.py`) and exits non-zero if its check fails.

## License

Code: MIT (see LICENSE). The book text and illustrations are not covered by this license.

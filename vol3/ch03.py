"""Chapter 3: Parsing Real Documents: Layout, Tables and Scans.

Run from the repo root:  python3 vol3/ch03.py
Optional real parser:    AIEV_PARSER=pdfplumber python3 vol3/ch03.py  (uv pip install pdfplumber==0.11.10)
Optional vision model:   AIEV_VISION=qwen2.5vl:3b python3 vol3/ch03.py (Ollama, page 2 image)
The warranty sheet is a fictional fixture (vol3/knowledge/layout/). Parts 1-3 use no
model. Part 1 is the naive cut, Part 2 the layout-aware parse, Part 3 the warranty
question against both.
"""
import base64
import os
import tempfile
from pathlib import Path

import _root  # noqa: F401

import layout as L
from ch13 import keyword_score

EU = "How long is the NW-500 warranty in the EU?"
PDF = L.FIXTURE.with_suffix(".pdf")


def top(question, texts, k=1):
    return sorted(texts, key=lambda t: -keyword_score(question, t))[:k]


def real_parser():
    import pdfplumber                         # optional; not needed for the book's trace
    with pdfplumber.open(PDF) as pdf:
        for p in pdf.pages:
            first = p.extract_text().splitlines()[1]
            print(f"  pdfplumber page={p.page_number} line 2: {first!r}")
            for t in p.extract_tables():
                print(f"  pdfplumber page={p.page_number} table rows={t[1:]}")


def real_vision(model):
    import json, urllib.request
    import pdfplumber
    with pdfplumber.open(PDF) as pdf:
        png = Path(tempfile.mkdtemp()) / "page2.png"
        pdf.pages[1].to_image(resolution=150).save(png)
    body = {"model": model, "stream": False, "options": {"temperature": 0},
            "messages": [{"role": "user", "images": [base64.b64encode(png.read_bytes()).decode()],
                          "content": "Copy the table on this page as CSV rows. Nothing else."}]}
    req = urllib.request.Request("http://localhost:11434/api/chat",
                                 json.dumps(body).encode(), {"Content-Type": "application/json"})
    print(f"  {model}: " + json.load(urllib.request.urlopen(req))["message"]["content"])


if __name__ == "__main__":
    doc = L.load()
    print("Part 1 (MM-071 Break): a plain extractor, then a 10-word cut")
    flat = L.naive_text(doc)
    cuts = L.fixed_chunks(flat)
    eu = next(c for c in cuts if " EU " in f" {c} ")
    print(f"  chunks={len(cuts)}  the EU row lands in: {eu!r}")

    print("\nPart 2 (MM-149 Fix): read the page")
    r = L.run(doc)
    for c in r["chunks"]:
        if c["kind"] == "row":
            print(f"  {c['id'].split(':')[1]}  {c['text'][27:]}")

    print(f"\nPart 3: top passage for {EU!r}")
    print(f"  naive:  {top(EU, cuts)[0]!r}")
    print(f"  layout: {top(EU, [c['text'] for c in r['chunks']])[0][27:]!r}")

    if os.environ.get("AIEV_PARSER") == "pdfplumber":   # see vol3/runs/README.md
        print("\nReal parser (pdfplumber) on the fixture PDF:")
        real_parser()
    if os.environ.get("AIEV_VISION"):                    # Model experiment
        print("\nVision model on page 2:")
        real_vision(os.environ["AIEV_VISION"])
